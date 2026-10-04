"""Problem 6 check: tool results and chat answers must match the database.

Run from the hw4 folder:
    .venv\\Scripts\\python tests\\check_chat_tools.py

Part A always runs (no model needed): each tool vs. a direct SQL query.
Part B runs only when PORTKEY_API_KEY and MODEL_NAME are set in hw4/.env:
three real chat questions, showing the tool calls and the agent's answer.
"""

import asyncio
import os
import sqlite3
import sys
from pathlib import Path

HW4 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW4 / "backend"))
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
# Test chats go to a scratch audit file, never to output/audit_trail.json.
os.environ.setdefault("CC_AUDIT_PATH", str(Path(__import__("tempfile").mkdtemp()) / "audit_trail.json"))

from pydantic_ai.messages import ToolCallPart, ToolReturnPart  # noqa: E402

import agent as agent_mod  # noqa: E402  (loads hw4/.env)
from models import ChatDeps  # noqa: E402
from tools import get_price, get_product_info, get_stock  # noqa: E402

DB = sqlite3.connect(f"file:{(HW4 / 'data' / 'campus_customs.db').as_posix()}?mode=ro", uri=True)

PRICE_Q = ("How much is the Yale Dad Hoodie?", "yale-dad-hoodie", None)
IN_STOCK_Q = ("Do you have the Yale Dad Hoodie in a medium?", "yale-dad-hoodie", "M")
OUT_Q = ("Is the Baseball Left Chest Crewneck available in XL?", "baseball-left-chest-crewneck", "XL")

results: list[tuple[str, bool]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{'  ' + detail if detail else ''}")


def db_price(pid: str) -> float:
    return DB.execute("SELECT price FROM catalogue WHERE product_id = ?", (pid,)).fetchone()[0]


def db_qty(pid: str, size: str) -> int:
    return DB.execute(
        "SELECT quantity FROM inventory WHERE product_id = ? AND size = ?", (pid, size)
    ).fetchone()[0]


def part_a() -> None:
    print("\n== Part A: tools vs. database ==")
    ctx = None  # the tools don't use ctx yet
    p = get_price(ctx, "Yale Dad Hoodie")
    check("get_price matches DB", p.found and p.price == db_price("yale-dad-hoodie"), f"tool={p.price} db={db_price('yale-dad-hoodie')}")

    s = get_stock(ctx, "Yale Dad Hoodie", "medium")
    check("get_stock (in stock) matches DB", s.sizes[0].quantity == db_qty("yale-dad-hoodie", "M") and s.sizes[0].in_stock, s.message)

    s = get_stock(ctx, "Baseball Left Chest Crewneck", "XL")
    check("get_stock (sold out) matches DB", s.sizes[0].quantity == db_qty("baseball-left-chest-crewneck", "XL") == 0 and not s.sizes[0].in_stock, s.message)

    s = get_stock(ctx, "Yale Dad Hoodie")
    total = DB.execute("SELECT sum(quantity) FROM inventory WHERE product_id='yale-dad-hoodie'").fetchone()[0]
    check("get_stock (all sizes) total matches DB", s.total_quantity == total and len(s.sizes) == 6, f"total={s.total_quantity}")

    i = get_product_info(ctx, "yale-dad-hoodie")
    check("get_product_info found by ID", i.found and i.price == db_price("yale-dad-hoodie"), f"in stock: {i.sizes_in_stock}")

    n = get_price(ctx, "Harvard Crimson Scarf")
    check("unknown product -> found=False", not n.found and n.price is None, n.message)

    a = get_price(ctx, "Yale Mom")
    check("ambiguous name -> candidates", not a.found and len(a.candidates) > 1, ", ".join(c.name for c in a.candidates))

    b = get_stock(ctx, "Yale Dad Hoodie", "XXXL")
    check("bad size -> size_valid=False", b.size_valid is False, b.message)

    inj = get_price(ctx, "x' OR '1'='1")
    check("SQL injection text is harmless", not inj.found, inj.message)


async def ask(question: str) -> tuple[str, list[str]]:
    result = await agent_mod.get_agent().run(question, deps=ChatDeps())
    calls = []
    for msg in result.all_messages():
        for part in msg.parts:
            if isinstance(part, ToolCallPart):
                calls.append(f"call   {part.tool_name}({part.args_as_dict()})")
            elif isinstance(part, ToolReturnPart):
                calls.append(f"return {part.tool_name}: {part.model_response_str()[:160]}")
    return result.output, calls


async def part_b() -> None:
    print("\n== Part B: live chat answers vs. database ==")
    if not (os.getenv("PORTKEY_API_KEY") and os.getenv("MODEL_NAME")):
        print("  SKIPPED: set PORTKEY_API_KEY and MODEL_NAME in hw4/.env, then rerun.")
        return
    print(f"  model: {os.getenv('MODEL_NAME')}")

    for question, pid, size in (PRICE_Q, IN_STOCK_Q, OUT_Q):
        answer, calls = await ask(question)
        print(f"\n  Q: {question}")
        for c in calls:
            print(f"     {c}")
        print(f"  A: {answer}")
        used_tool = any(c.startswith("call") for c in calls)
        if size is None:
            expected = f"{db_price(pid):.2f}"
            check("price answer matches DB", used_tool and expected in answer, f"DB price ${expected}")
        else:
            qty = db_qty(pid, size)
            if qty > 0:
                check("in-stock answer matches DB", used_tool and str(qty) in answer, f"DB {size} qty = {qty}")
            else:
                said_out = any(w in answer.lower() for w in ("out of stock", "sold out", "not in stock", "none in stock", "0 in stock", "unavailable", "not available"))
                check("out-of-stock answer matches DB", used_tool and said_out, f"DB {size} qty = 0")


if __name__ == "__main__":
    part_a()
    asyncio.run(part_b())
    passed = sum(ok for _, ok in results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)
