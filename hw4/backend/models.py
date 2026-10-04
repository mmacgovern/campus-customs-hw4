"""Pydantic types shared by the chat route and the agent."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

MAX_MESSAGE_CHARS = 1000
MAX_HISTORY_MESSAGES = 20
MAX_SEARCH_RESULTS = 12


class ProductCard(BaseModel):
    """A product card the chat sends to the page (same fields the Products grid shows)."""

    product_id: str
    name: str
    price: float
    short_description: str
    image_url: str = Field(description='Image path served by the API, e.g. "/images/<file>.jpg".')


class ChatMessage(BaseModel):
    """One earlier turn of the conversation."""

    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class SavedChatMessage(BaseModel):
    """A message from the chat_history table, as reloaded into the chat panel."""

    role: Literal["user", "assistant"]
    content: str
    created_at: str


class ChatHistoryReply(BaseModel):
    """What GET /chat/history returns (empty for guests)."""

    messages: list[SavedChatMessage] = Field(default_factory=list)


class PageContext(BaseModel):
    """Which page the shopper is on when they send a message."""

    path: str = Field(max_length=200)
    product_id: str | None = Field(default=None, max_length=100, pattern=r"^[a-z0-9-]+$")


class ChatRequest(BaseModel):
    """What the chat panel posts to POST /chat.

    `history` is only used for guests; a logged-in customer's history is
    loaded from the database instead.
    """

    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    history: list[ChatMessage] = Field(default_factory=list, max_length=MAX_HISTORY_MESSAGES)
    page: PageContext | None = None


class ChatReply(BaseModel):
    """What POST /chat returns to the chat panel.

    `products` holds the cards from this turn's catalogue search (at most
    MAX_SEARCH_RESULTS). It is empty when no search ran or nothing matched.
    """

    reply: str
    products: list[ProductCard] = Field(default_factory=list, max_length=MAX_SEARCH_RESULTS)


@dataclass
class ChatDeps:
    """Per-request context handed to the agent and its tools.

    Customer fields come from the login session on the server, never from
    the browser. The password hash is never included.
    """

    user_id: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    # Page context sent by the chat panel; the product is checked against the catalogue.
    page_path: str | None = None
    page_product_id: str | None = None
    page_product_name: str | None = None
    # Filled by search_catalogue; the /chat route returns it as ChatReply.products.
    search_results: list[ProductCard] | None = None


# ---------- tool lookup results ----------
# Every lookup says whether it found the product, so the agent can say
# "not found" instead of guessing. Prices and quantities only ever come
# from these models, which are filled straight from the database.


class ProductMatch(BaseModel):
    """A short candidate when a product name is ambiguous or not found."""

    product_id: str
    name: str
    price: float


class SizeStock(BaseModel):
    size: str
    quantity: int
    in_stock: bool
    # True when 1 to LOW_STOCK_THRESHOLD (3) are left: the agent says "only N left".
    low_stock: bool = False


class ProductInfo(BaseModel):
    """Result of get_product_info."""

    found: bool
    message: str
    product_id: str | None = None
    name: str | None = None
    garment_type: str | None = None
    description: str | None = None
    colors: list[str] = Field(default_factory=list)
    price: float | None = None
    sizes_in_stock: list[str] = Field(default_factory=list)
    sizes_sold_out: list[str] = Field(default_factory=list)
    low_stock_sizes: list[SizeStock] = Field(default_factory=list)
    candidates: list[ProductMatch] = Field(default_factory=list)


class PriceInfo(BaseModel):
    """Result of get_price."""

    found: bool
    message: str
    product_id: str | None = None
    name: str | None = None
    price: float | None = None
    currency: str = "USD"
    candidates: list[ProductMatch] = Field(default_factory=list)


class StockInfo(BaseModel):
    """Result of get_stock: every size, or just the size the customer asked about."""

    found: bool
    message: str
    product_id: str | None = None
    name: str | None = None
    requested_size: str | None = None
    size_valid: bool | None = None
    sizes: list[SizeStock] = Field(default_factory=list)
    total_quantity: int | None = None
    candidates: list[ProductMatch] = Field(default_factory=list)


Category = Literal["hoodie", "crewneck", "t-shirt", "quarter-zip", "jacket", "long-sleeve"]


class CatalogueSearchResult(BaseModel):
    """Result of search_catalogue. These cards are also shown on the page."""

    found: bool
    message: str
    query: str
    category: str | None = None
    color: str | None = None
    max_price: float | None = None
    total_matches: int
    products: list[ProductCard] = Field(default_factory=list, max_length=MAX_SEARCH_RESULTS)


class SimilarItem(BaseModel):
    """A similar product that is in stock in the size the customer wanted."""

    product_id: str
    name: str
    price: float
    size: str
    quantity: int
    low_stock: bool


class AlternativesResult(BaseModel):
    """Result of suggest_alternatives: in-stock options when a size is unavailable."""

    found: bool
    message: str
    product_id: str | None = None
    name: str | None = None
    requested_size: str | None = None
    size_valid: bool | None = None
    requested_size_in_stock: bool | None = None
    other_sizes_in_stock: list[SizeStock] = Field(default_factory=list)
    similar_in_stock: list[SimilarItem] = Field(default_factory=list)
    candidates: list[ProductMatch] = Field(default_factory=list)
