"""Problem 9 check: categories for the Products filter, suggest_alternatives,
and the low-stock rule, all compared with the database.

Run from the hw4 folder:
    .venv\\Scripts\\python tests\\check_usability.py

The two chat questions use the real model when hw4/.env is set; otherwise a
scripted fake model calls the same tools, so the route wiring is still tested.
"""

import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path

HW4 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW4 / "backend"))
os.chdir(HW4 / "backend")
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
# Test chats go to a scratch audit file, never to output/audit_trail.json.
os.environ.setdefault("CC_AUDIT_PATH", str(Path(__import__("tempfile").mkdtemp()) / "audit_trail.json"))

from fastapi.testclient import TestClient  # noqa: E402
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart  # noqa: E402
from pydantic_ai.models.function import AgentInfo, FunctionModel  # noqa: E402

import agent as agent_mod  # noqa: E402  (loads hw4/.env)
from main import app  # noqa: E402
from models import ChatDeps  # noqa: E402
from tools import CATEGORY_SQL, LOW_STOCK_THRESHOLD, get_stock, suggest_alternatives  # noqa: E402

LIVE = bool(os.getenv("PORTKEY_API_KEY") and os.getenv("MODEL_NAME"))
DB = sqlite3.connect(f"file:{(HW4 / 'data' / 'campus_customs.db').as_posix()}?mode=ro", uri=True)
results: list[bool] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{'  -> ' + detail if detail else ''}")


class Ctx:
    def __init__(self) -> None:
        self.deps = ChatDeps()


def part_products_filter(client: TestClient) -> None:
    print("\n== 1. Products page data: category for the filter ==")
    products = client.get("/api/products").json()
    counts = Counter(p["category"] for p in products)
    for cat, sql in CATEGORY_SQL.items():
        db_n = DB.execute(f"SELECT count(*) FROM catalogue WHERE {sql}").fetchone()[0]
        check(f"category {cat!r} count matches DB", counts[cat] == db_n, f"{counts[cat]} = {db_n}")
    cheapest = min(products, key=lambda p: p["price"])["price"]
    check("price sort data: lowest price matches DB", cheapest == DB.execute("SELECT min(price) FROM catalogue").fetchone()[0], f"${cheapest:.2f}")


def part_tools() -> None:
    print("\n== 3. suggest_alternatives vs. DB (Baseball Left Chest Crewneck, XL) ==")
    pid = "baseball-left-chest-crewneck"
    ctx = Ctx()
    r = suggest_alternatives(ctx, "Baseball Left Chest Crewneck", "XL")
    db_xl = DB.execute("SELECT quantity FROM inventory WHERE product_id=? AND size='XL'", (pid,)).fetchone()[0]
    check("requested size reported out of stock", r.requested_size_in_stock is False and db_xl == 0)
    db_other = [s for s, q in DB.execute("SELECT size, quantity FROM inventory WHERE product_id=? AND quantity>0 AND size!='XL' ORDER BY id", (pid,))]
    check("other in-stock sizes match DB", [s.size for s in r.other_sizes_in_stock] == db_other, ", ".join(db_other))
    ok = all(
        DB.execute("SELECT quantity FROM inventory WHERE product_id=? AND size='XL'", (s.product_id,)).fetchone()[0] == s.quantity > 0
        for s in r.similar_in_stock
    )
    check("every similar item really in stock in XL (DB qty)", ok and 0 < len(r.similar_in_stock) <= 4,
          "; ".join(f"{s.name} ({s.quantity})" for s in r.similar_in_stock))
    same_cat = all("crewneck" in DB.execute("SELECT garment_type FROM catalogue WHERE product_id=?", (s.product_id,)).fetchone()[0] for s in r.similar_in_stock)
    check("similar items are the same category (crewneck)", same_cat)
    check("similar items sent to the page as cards", [c.product_id for c in ctx.deps.search_results] == [s.product_id for s in r.similar_in_stock])

    print("\n== 4. Low-stock rule vs. DB ==")
    s = get_stock(Ctx(), "Basic Hoodie Big Yale", "XL")
    db_q = DB.execute("SELECT quantity FROM inventory WHERE product_id='basic-hoodie-big-yale' AND size='XL'").fetchone()[0]
    check("Basic Hoodie Big Yale XL flagged low_stock", s.sizes[0].low_stock and s.sizes[0].quantity == db_q, s.message)
    high = get_stock(Ctx(), "Basic Hoodie Big Yale", "M")
    check("a well-stocked size is NOT flagged", not high.sizes[0].low_stock, high.message)
    flagged = 0
    for (p,) in DB.execute("SELECT product_id FROM catalogue"):
        for z in get_stock(Ctx(), p).sizes:
            flagged += z.low_stock
    db_low = DB.execute("SELECT count(*) FROM inventory WHERE quantity BETWEEN 1 AND ?", (LOW_STOCK_THRESHOLD,)).fetchone()[0]
    check("all 612 sizes: low_stock flags match DB (1-3 left)", flagged == db_low, f"{flagged} = {db_low}")


def scripted(*steps):
    """Fake LLM: make the given tool calls in order, then reply with every tool message."""
    def fn(messages, info: AgentInfo):
        done = sum(isinstance(p, ToolReturnPart) for m in messages for p in m.parts)
        if done < len(steps):
            return ModelResponse(parts=[ToolCallPart(*steps[done])])
        msgs = [p.content.message for m in messages for p in m.parts if isinstance(p, ToolReturnPart)]
        return ModelResponse(parts=[TextPart(" ".join(msgs))])
    return FunctionModel(fn)


def part_chat(client: TestClient) -> None:
    print(f"\n== Chat through /chat ({'LIVE ' + os.getenv('MODEL_NAME', '') if LIVE else 'fake model, no .env yet'}) ==")
    if not LIVE:
        os.environ.update(PORTKEY_API_KEY="dummy-not-real", MODEL_NAME="gpt-5.6-luna")
        agent_mod.get_agent.cache_clear()
    agent = agent_mod.get_agent()

    q1 = "Is the Baseball Left Chest Crewneck available in XL?"
    fake1 = scripted(("get_stock", {"product": "Baseball Left Chest Crewneck", "size": "XL"}),
                     ("suggest_alternatives", {"product": "Baseball Left Chest Crewneck", "size": "XL"}))
    q2 = "Do you have the Basic Hoodie Big Yale in XL?"
    fake2 = scripted(("get_stock", {"product": "Basic Hoodie Big Yale", "size": "XL"}))

    for q, fake, expect in ((q1, fake1, "alternatives"), (q2, fake2, "low")):
        if LIVE:
            body = client.post("/chat", json={"message": q, "page": {"path": "/"}}).json()
        else:
            with agent.override(model=fake):
                body = client.post("/chat", json={"message": q, "page": {"path": "/"}}).json()
        print(f"  Q: {q}\n  A: {body['reply']}\n     cards: {[p['name'] for p in body['products']]}")
        text = body["reply"].lower()
        if expect == "alternatives":
            check("says out of stock", "out of stock" in text or "sold out" in text)
            check("offers in-stock sizes or similar items + cards", len(body["products"]) > 0 and any(z in body["reply"] for z in ("L", "XXL", "S")))
        else:
            check('says "only 2 left"', "only 2 left" in text)


if __name__ == "__main__":
    client = TestClient(app)
    part_products_filter(client)
    part_tools()
    part_chat(client)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)
