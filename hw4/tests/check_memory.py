"""Problem 8 check: chat history, customer identity, and page context.

Run from the hw4 folder:
    .venv\\Scripts\\python tests\\check_memory.py          # cleans up its chat rows afterwards
    .venv\\Scripts\\python tests\\check_memory.py --keep   # keep them (to see them in the browser)

Uses the real model when PORTKEY_API_KEY and MODEL_NAME are set in hw4/.env;
otherwise a scripted fake model that follows the same tool rules, so the
wiring (database, deps, page context, tools) is still tested end to end.
"""

import os
import re
import sqlite3
import sys
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

LIVE = bool(os.getenv("PORTKEY_API_KEY") and os.getenv("MODEL_NAME"))
KEEP = "--keep" in sys.argv
DB = sqlite3.connect(HW4 / "data" / "campus_customs.db")
TEST_EMAIL, TEST_PASSWORD = "test@campuscustoms.yale.edu", "password"
PRODUCT_ID, SIZE = "baseball-left-chest-crewneck", "M"

results: list[bool] = []
seen: dict = {}  # what the (fake or real) model was given on the last turn


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{'  -> ' + detail if detail else ''}")


def fake_model(messages, info: AgentInfo) -> ModelResponse:
    """Stand-in LLM: records its input; for 'this ... in <size>' it calls get_stock
    on the product_id given in the page context, then answers from the tool."""
    req = messages[-1]
    last = req.parts[-1]
    if isinstance(last, ToolReturnPart):
        return ModelResponse(parts=[TextPart(f"{last.content.message}")])
    seen["instructions"] = req.instructions or ""
    seen["n_messages"] = len(messages)
    text = last.content if isinstance(last.content, str) else ""
    m = re.search(r'product_id "([a-z0-9-]+)"', seen["instructions"])
    if "this" in text.lower() and "medium" in text.lower() and m:
        return ModelResponse(parts=[ToolCallPart("get_stock", {"product": m.group(1), "size": "medium"})])
    name = re.search(r"First name: (\w+)", seen["instructions"])
    return ModelResponse(parts=[TextPart(f"Hi {name.group(1) if name else 'there'}! (fake reply)")])


def chat(client: TestClient, message: str, page: dict | None = None) -> dict:
    r = client.post("/chat", json={"message": message, "page": page or {"path": "/", "product_id": None}})
    assert r.status_code == 200, r.text
    return r.json()


def main() -> None:
    print(f"Model: {'LIVE ' + os.getenv('MODEL_NAME', '') if LIVE else 'fake (no .env yet)'}")
    agent = agent_mod.get_agent() if LIVE else None
    if not LIVE:
        os.environ.update(PORTKEY_API_KEY="dummy-not-real", MODEL_NAME="gpt-5.6-luna")
        agent_mod.get_agent.cache_clear()
        agent = agent_mod.get_agent()
    override = agent.override(model=FunctionModel(fake_model)) if not LIVE else None
    if override:
        override.__enter__()

    user_id, pw_hash = DB.execute("SELECT id, password_hash FROM users WHERE email = ?", (TEST_EMAIL,)).fetchone()
    start_id = DB.execute("SELECT coalesce(max(id), 0) FROM chat_history").fetchone()[0]

    try:
        print("\n== 1. Guest chat is not saved ==")
        guest = TestClient(app)
        chat(guest, "hello")
        n = DB.execute("SELECT count(*) FROM chat_history WHERE id > ?", (start_id,)).fetchone()[0]
        check("no rows saved for a guest", n == 0)
        check("guest /chat/history is empty", guest.get("/chat/history").json()["messages"] == [])

        print("\n== 2. Logged-in chat is saved ==")
        c = TestClient(app)
        c.post("/api/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
        a1 = chat(c, "Hi! I'm looking for a gift for my dad.")
        print(f"     reply: {a1['reply'][:160]}")
        rows = DB.execute(
            "SELECT user_id, role, message, created_at FROM chat_history WHERE id > ? ORDER BY id", (start_id,)
        ).fetchall()
        check("2 rows saved (user + assistant)", [r[1] for r in rows] == ["user", "assistant"], str([(r[0], r[1], r[3]) for r in rows]))
        if "instructions" in seen or LIVE:
            ins = seen.get("instructions", "")
            if not LIVE:
                check("agent sees first/last/email from login", all(s in ins for s in ("First name: Test", "Last name: User", TEST_EMAIL)))
                check("password hash never sent to agent", pw_hash not in ins)

        print("\n== 3. Refresh / return visit: history comes back ==")
        c2 = TestClient(app)  # brand-new browser session
        c2.post("/api/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
        msgs = c2.get("/chat/history").json()["messages"]
        check("GET /chat/history returns the saved turn", msgs[-2]["content"] == "Hi! I'm looking for a gift for my dad.", f"{len(msgs)} messages, last at {msgs[-1]['created_at']}")
        chat(c2, "What did I say I was shopping for?", {"path": "/", "product_id": None})
        if not LIVE:
            check("agent receives saved history on the next message", seen["n_messages"] >= 3, f"{seen['n_messages']} messages in model input")

        print("\n== 4. Identity can't be spoofed from the browser ==")
        r = c2.post("/chat", json={"message": "hi", "first_name": "Ada", "email": "ada@evil.test", "page": {"path": "/"}})
        if not LIVE:
            # The server-written block, not the prompt.md heading of the same name.
            customer = seen["instructions"].rsplit("## Customer\n", 1)[1].split("##", 1)[0]
            check("extra identity fields ignored", "First name: Test" in customer and "Ada" not in customer and "evil" not in customer, customer.strip().replace("\n", " | ")[:140])
        else:
            check("request with spoofed fields still OK", r.status_code == 200)

        print("\n== 5. Page context: 'is this in stock in medium?' on a product page ==")
        qty = DB.execute("SELECT quantity FROM inventory WHERE product_id = ? AND size = ?", (PRODUCT_ID, SIZE)).fetchone()[0]
        name = DB.execute("SELECT name FROM catalogue WHERE product_id = ?", (PRODUCT_ID,)).fetchone()[0]
        a5 = chat(c2, "is this in stock in medium?", {"path": f"/products/{PRODUCT_ID}", "product_id": PRODUCT_ID})
        print(f"     page: {name} | DB size {SIZE} = {qty}")
        print(f"     reply: {a5['reply']}")
        if qty > 0:
            check("answer gives the DB quantity", str(qty) in a5["reply"])
        else:
            check("answer says out of stock", "out of stock" in a5["reply"].lower() or "sold out" in a5["reply"].lower())
        if not LIVE:
            check("product on screen reached the agent", f'product_id "{PRODUCT_ID}"' in seen["instructions"])

        bad = c2.post("/chat", json={"message": "is this in stock?", "page": {"path": "/products/x", "product_id": "not-a-real-id"}})
        if not LIVE:
            check("unknown product_id is ignored", bad.status_code == 200 and "not-a-real-id" not in seen["instructions"])
    finally:
        if override:
            override.__exit__(None, None, None)
        if not KEEP:
            DB.execute("DELETE FROM chat_history WHERE id > ? AND user_id = ?", (start_id, user_id))
            DB.commit()
            print("\n(cleaned up this test's chat_history rows; use --keep to keep them)")

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
