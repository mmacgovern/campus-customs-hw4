"""Tools the Campus Customs agent can call.

All tools are read-only (the database is opened with mode=ro) and use
parameterised SQL. Prices and quantities in the agent's answers must come
from these results.
"""

import json
import re
import sqlite3
from contextlib import closing

from pydantic_ai import RunContext, Tool

from db import get_db
from models import (
    MAX_SEARCH_RESULTS,
    AlternativesResult,
    CatalogueSearchResult,
    Category,
    ChatDeps,
    PriceInfo,
    ProductInfo,
    ProductCard,
    ProductMatch,
    SimilarItem,
    SizeStock,
    StockInfo,
)

SIZES = ["XS", "S", "M", "L", "XL", "XXL"]
SIZE_ALIASES = {
    "EXTRA SMALL": "XS", "X-SMALL": "XS", "XSMALL": "XS",
    "SMALL": "S", "SM": "S",
    "MEDIUM": "M", "MED": "M", "MD": "M",
    "LARGE": "L", "LG": "L",
    "EXTRA LARGE": "XL", "X-LARGE": "XL", "XLARGE": "XL",
    "XX-LARGE": "XXL", "XXLARGE": "XXL", "2XL": "XXL", "2X": "XXL", "EXTRA EXTRA LARGE": "XXL",
}
SIZE_ORDER_SQL = (
    "CASE size WHEN 'XS' THEN 0 WHEN 'S' THEN 1 WHEN 'M' THEN 2 "
    "WHEN 'L' THEN 3 WHEN 'XL' THEN 4 WHEN 'XXL' THEN 5 ELSE 6 END"
)
MAX_CANDIDATES = 5
LOW_STOCK_THRESHOLD = 3  # 1-3 left in a size counts as low stock
MAX_SIMILAR = 4


# ---------- helpers ----------

def normalize_size(size: str) -> str | None:
    s = size.strip().upper()
    if s in SIZES:
        return s
    return SIZE_ALIASES.get(s)


def _match(row: sqlite3.Row) -> ProductMatch:
    return ProductMatch(product_id=row["product_id"], name=row["name"], price=row["price"])


def find_product(
    conn: sqlite3.Connection, product: str
) -> tuple[sqlite3.Row | None, list[ProductMatch]]:
    """Resolve a product ID or name to one catalogue row.

    Returns (row, []) on a single match, or (None, candidates) when the name
    matches several products or none.
    """
    text = product.strip()
    # 1. Exact product ID, then exact name (case-insensitive).
    row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (text.lower(),)).fetchone()
    if row is None:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE lower(name) = lower(?)", (text,)
        ).fetchone()
    if row is not None:
        return row, []

    # 2. Every word must appear in the name, ID, or tags.
    words = [w for w in re.split(r"[^a-z0-9]+", text.lower()) if w]
    if not words:
        return None, []
    where = " AND ".join(
        ["(lower(name) LIKE ? OR product_id LIKE ? OR lower(search_tags) LIKE ?)"] * len(words)
    )
    params: list[str] = []
    for w in words:
        params += [f"%{w}%"] * 3
    rows = conn.execute(
        f"SELECT * FROM catalogue WHERE {where} ORDER BY name LIMIT ?",
        (*params, MAX_CANDIDATES + 1),
    ).fetchall()
    if len(rows) == 1:
        return rows[0], []
    return None, [_match(r) for r in rows[:MAX_CANDIDATES]]


def not_found_message(product: str, candidates: list[ProductMatch]) -> str:
    if candidates:
        return (
            f'"{product}" matches more than one product. Ask the customer which one they mean.'
        )
    return f'No product called "{product}" was found in the Campus Customs catalogue.'


def stock_rows(conn: sqlite3.Connection, product_id: str) -> list[SizeStock]:
    rows = conn.execute(
        f"SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY {SIZE_ORDER_SQL}",
        (product_id,),
    ).fetchall()
    return [size_stock(r["size"], r["quantity"]) for r in rows]


def size_stock(size: str, quantity: int) -> SizeStock:
    return SizeStock(
        size=size,
        quantity=quantity,
        in_stock=quantity > 0,
        low_stock=0 < quantity <= LOW_STOCK_THRESHOLD,
    )


# Each category groups the messy garment_type values in the catalogue.
# Used by the search tool (SQL) and by /api/products (category_of), so the
# Products page filter and the chatbot agree.
CATEGORY_PATTERNS: dict[str, str] = {
    "hoodie": "hood",
    "crewneck": "crewneck",
    "t-shirt": "t-shirt",
    "quarter-zip": "quarter-zip",
    "jacket": "jacket",
    "long-sleeve": "long-sleeve",
}
CATEGORY_SQL: dict[str, str] = {
    name: f"garment_type LIKE '%{pattern}%'" for name, pattern in CATEGORY_PATTERNS.items()
}


def category_of(garment_type: str) -> str:
    g = garment_type.lower()
    for name, pattern in CATEGORY_PATTERNS.items():
        if pattern in g:
            return name
    return "other"
STOP_WORDS = {
    "a", "an", "the", "and", "or", "with", "for", "of", "in", "on", "any", "some",
    "do", "you", "have", "what", "show", "me", "got", "gear", "merch", "items",
    "item", "stuff", "clothes", "apparel", "products", "product",
}
SYNONYMS = {"tee": "t-shirt", "tshirt": "t-shirt", "hoody": "hoodie", "hoodies": "hoodie"}
SHORT_DESCRIPTION_CHARS = 110


def short_description(text: str) -> str:
    if len(text) <= SHORT_DESCRIPTION_CHARS:
        return text
    cut = text[:SHORT_DESCRIPTION_CHARS].rsplit(" ", 1)[0]
    return cut.rstrip(",;:.") + "\u2026"


def card_from_row(row: sqlite3.Row) -> ProductCard:
    return ProductCard(
        product_id=row["product_id"],
        name=row["name"],
        price=row["price"],
        short_description=short_description(row["description"]),
        image_url=f"/images/{row['image_file_path'].rsplit('/', 1)[-1]}",
    )


def search_words(query: str) -> list[str]:
    words = []
    for w in re.split(r"[^a-z0-9-]+", query.lower()):
        w = w.strip("-")
        if not w or w in STOP_WORDS:
            continue
        w = SYNONYMS.get(w, w)
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]  # hoodies -> hoodie, shirts -> shirt
        words.append(w)
    return words


# ---------- tools ----------

def search_catalogue(
    ctx: RunContext[ChatDeps],
    query: str = "",
    category: Category | None = None,
    color: str | None = None,
    max_price: float | None = None,
    limit: int = MAX_SEARCH_RESULTS,
) -> CatalogueSearchResult:
    """Search the catalogue for products matching what the customer is looking for.
    The matches are shown to the customer as product cards on the page.

    Args:
        query: Keywords such as a college, sport, school, design or style
            (e.g. "Davenport", "hockey", "vintage bulldog"). Leave empty to list a whole category.
        category: Type of item, if the customer named one.
        color: A color the customer asked for (e.g. "navy", "gray").
        max_price: Highest price in USD, if the customer gave a budget.
        limit: Maximum number of products to return (at most 12).
    """
    limit = max(1, min(limit, MAX_SEARCH_RESULTS))
    clauses: list[str] = []
    params: list[object] = []
    if category:
        clauses.append(CATEGORY_SQL[category])
    if color and color.strip():
        clauses.append("lower(colors) LIKE ?")
        params.append(f"%{color.strip().lower()}%")
    if max_price is not None:
        clauses.append("price <= ?")
        params.append(max_price)
    for w in search_words(query):
        clauses.append(
            "(lower(name) LIKE ? OR lower(description) LIKE ? OR lower(search_tags) LIKE ? "
            "OR lower(garment_type) LIKE ? OR lower(colors) LIKE ?)"
        )
        params += [f"%{w}%"] * 5
    where = " AND ".join(clauses) or "1 = 1"

    with closing(get_db()) as conn:
        total = conn.execute(f"SELECT count(*) FROM catalogue WHERE {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM catalogue WHERE {where} ORDER BY name LIMIT ?", (*params, limit)
        ).fetchall()

    cards = [card_from_row(r) for r in rows]
    # Remember the cards so the /chat route can send them to the page.
    ctx.deps.search_results = cards

    if not cards:
        message = "No products match this search. Tell the customer we don't carry that."
    elif total > len(cards):
        message = f"{total} products match; showing the first {len(cards)}."
    else:
        message = f"{total} product(s) match."
    return CatalogueSearchResult(
        found=bool(cards),
        message=message,
        query=query,
        category=category,
        color=color,
        max_price=max_price,
        total_matches=total,
        products=cards,
    )


def get_product_info(ctx: RunContext[ChatDeps], product: str) -> ProductInfo:
    """Look up a product's details: description, garment type, colors, price,
    and which sizes are in stock or sold out.

    Args:
        product: The product's name (e.g. "Yale Dad Hoodie") or product ID.
    """
    with closing(get_db()) as conn:
        row, candidates = find_product(conn, product)
        if row is None:
            return ProductInfo(
                found=False, message=not_found_message(product, candidates), candidates=candidates
            )
        sizes = stock_rows(conn, row["product_id"])
    return ProductInfo(
        found=True,
        message="Product found.",
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        colors=json.loads(row["colors"]),
        price=row["price"],
        sizes_in_stock=[s.size for s in sizes if s.in_stock],
        sizes_sold_out=[s.size for s in sizes if not s.in_stock],
        low_stock_sizes=[s for s in sizes if s.low_stock],
    )


def get_price(ctx: RunContext[ChatDeps], product: str) -> PriceInfo:
    """Look up the current price of a product, in US dollars.

    Args:
        product: The product's name (e.g. "Yale Dad Hoodie") or product ID.
    """
    with closing(get_db()) as conn:
        row, candidates = find_product(conn, product)
    if row is None:
        return PriceInfo(
            found=False, message=not_found_message(product, candidates), candidates=candidates
        )
    return PriceInfo(
        found=True,
        message="Price found.",
        product_id=row["product_id"],
        name=row["name"],
        price=row["price"],
    )


def get_stock(ctx: RunContext[ChatDeps], product: str, size: str | None = None) -> StockInfo:
    """Look up how many units of a product are in stock. Pass a size when the
    customer asks about one; leave it out to get every size.

    Args:
        product: The product's name (e.g. "Yale Dad Hoodie") or product ID.
        size: Optional size: XS, S, M, L, XL or XXL (words like "medium" also work).
    """
    with closing(get_db()) as conn:
        row, candidates = find_product(conn, product)
        if row is None:
            return StockInfo(
                found=False, message=not_found_message(product, candidates), candidates=candidates
            )
        sizes = stock_rows(conn, row["product_id"])

    base = dict(found=True, product_id=row["product_id"], name=row["name"])

    if size is None:
        total = sum(s.quantity for s in sizes)
        return StockInfo(**base, message="Stock for every size.", sizes=sizes, total_quantity=total)

    wanted = normalize_size(size)
    if wanted is None:
        return StockInfo(
            **base,
            requested_size=size,
            size_valid=False,
            message=f'"{size}" is not a size we carry. Sizes are {", ".join(SIZES)}.',
            sizes=sizes,
        )
    match = [s for s in sizes if s.size == wanted]
    qty = match[0].quantity if match else 0
    if qty == 0:
        msg = (
            f"{row['name']} in size {wanted} is OUT OF STOCK (0 available). "
            "Call suggest_alternatives to offer other sizes or similar items."
        )
    elif qty <= LOW_STOCK_THRESHOLD:
        msg = f"{row['name']} in size {wanted}: ONLY {qty} LEFT (low stock)."
    else:
        msg = f"{row['name']} in size {wanted}: {qty} in stock."
    return StockInfo(
        **base,
        requested_size=wanted,
        size_valid=True,
        message=msg,
        sizes=match or [size_stock(wanted, 0)],
        total_quantity=qty,
    )


def _shared_words(row: sqlite3.Row) -> set[str]:
    words: set[str] = set()
    for field in ("search_tags", "colors"):
        for item in json.loads(row[field]):
            words.update(w for w in re.split(r"[^a-z0-9]+", item.lower()) if len(w) > 2)
    return words - {"yale", "college", "merch", "university"}


def suggest_alternatives(ctx: RunContext[ChatDeps], product: str, size: str) -> AlternativesResult:
    """When a product is out of stock in a size (or the customer wants something
    similar), find in-stock options: other sizes of the same product, and similar
    products that are in stock in the requested size. The similar products are
    also shown to the customer as product cards on the page.

    Args:
        product: The product's name or product ID.
        size: The size the customer wanted: XS, S, M, L, XL or XXL.
    """
    wanted = normalize_size(size)
    with closing(get_db()) as conn:
        row, candidates = find_product(conn, product)
        if row is None:
            return AlternativesResult(
                found=False, message=not_found_message(product, candidates), candidates=candidates
            )
        base = dict(found=True, product_id=row["product_id"], name=row["name"])
        if wanted is None:
            return AlternativesResult(
                **base,
                requested_size=size,
                size_valid=False,
                message=f'"{size}" is not a size we carry. Sizes are {", ".join(SIZES)}.',
            )

        sizes = stock_rows(conn, row["product_id"])
        requested = next((s for s in sizes if s.size == wanted), size_stock(wanted, 0))
        other_sizes = [s for s in sizes if s.in_stock and s.size != wanted]

        # Same category, in stock in the wanted size, not the product itself.
        category = category_of(row["garment_type"])
        if category in CATEGORY_SQL:
            cat_sql, cat_params = CATEGORY_SQL[category], ()
        else:
            cat_sql, cat_params = "garment_type = ?", (row["garment_type"],)
        others = conn.execute(
            "SELECT c.*, i.quantity FROM catalogue c JOIN inventory i USING (product_id) "
            f"WHERE {cat_sql} AND i.size = ? AND i.quantity > 0 AND c.product_id != ?",
            (*cat_params, wanted, row["product_id"]),
        ).fetchall()

    # Rank by shared tags/colors, then by closeness in price.
    mine = _shared_words(row)
    ranked = sorted(
        others,
        key=lambda r: (-len(mine & _shared_words(r)), abs(r["price"] - row["price"]), r["name"]),
    )[:MAX_SIMILAR]
    similar = [
        SimilarItem(
            product_id=r["product_id"],
            name=r["name"],
            price=r["price"],
            size=wanted,
            quantity=r["quantity"],
            low_stock=r["quantity"] <= LOW_STOCK_THRESHOLD,
        )
        for r in ranked
    ]
    # Show the similar items as product cards on the page.
    if ranked:
        ctx.deps.search_results = [card_from_row(r) for r in ranked]

    if requested.in_stock:
        status = f"{row['name']} in {wanted} is in stock ({requested.quantity})."
    else:
        status = f"{row['name']} in {wanted} is out of stock."
    others_txt = ", ".join(s.size for s in other_sizes) or "none"
    message = (
        f"{status} Other sizes in stock: {others_txt}. "
        f"{len(similar)} similar item(s) in stock in {wanted} (shown as cards on the page)."
    )
    return AlternativesResult(
        **base,
        message=message,
        requested_size=wanted,
        size_valid=True,
        requested_size_in_stock=requested.in_stock,
        other_sizes_in_stock=other_sizes,
        similar_in_stock=similar,
    )


AGENT_TOOLS: list[Tool[ChatDeps]] = [
    Tool(search_catalogue),
    Tool(get_product_info),
    Tool(get_price),
    Tool(get_stock),
    Tool(suggest_alternatives),
]
