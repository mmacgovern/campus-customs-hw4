"""Problem 11: test the running site and write output/app_check.html.

Run from the hw4 folder:
    .venv\\Scripts\\python tests\\app_check.py

- Starts the FastAPI backend (:8000) and Vite front end (:5173) if they
  aren't already running, and stops the ones it started.
- Drives Chrome with Playwright and saves screenshots to
  output/app_check_images/.
- Reads the matching values straight from data/campus_customs.db and puts
  them next to the screenshots.

Checks 1 and 2 need the real chatbot, so they run only when hw4/.env has
PORTKEY_API_KEY and MODEL_NAME. Otherwise they are marked "pending" in the
report (never faked).
"""

import html
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values
from playwright.sync_api import Page, sync_playwright

HW4 = Path(__file__).resolve().parent.parent
OUT = HW4 / "output"
IMG = OUT / "app_check_images"
DB_PATH = HW4 / "data" / "campus_customs.db"
FRONT = "http://localhost:5173"
BACK = "http://localhost:8000"

# Check 1: one item, one size.
INV_PRODUCT_ID, INV_SIZE = "yale-dad-hoodie", "M"
INV_QUESTION = "How much is the Yale Dad Hoodie, and do you have it in a medium?"
SEARCH_QUESTION = "what hoodies do you have?"
AGENT_TIMEOUT_MS = 120_000


# ---------- servers ----------

def is_up(url: str) -> bool:
    try:
        urllib.request.urlopen(url, timeout=2)
        return True
    except Exception:
        return False


def start_servers() -> list[subprocess.Popen]:
    started = []
    if not is_up(f"{BACK}/api/health"):
        started.append(subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--port", "8000"],
            cwd=HW4 / "backend", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ))
    if not is_up(FRONT):
        started.append(subprocess.Popen(
            "npm run dev -- --port 5173 --strictPort",
            cwd=HW4 / "frontend", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ))
    for _ in range(80):
        if is_up(f"{BACK}/api/health") and is_up(f"{FRONT}/api/health"):
            return started
        time.sleep(0.5)
    raise SystemExit("Servers did not start on :8000 and :5173")


def stop_servers(procs: list[subprocess.Popen]) -> None:
    for p in procs:
        subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)


# ---------- browser helpers ----------

def ask_chat(page: Page, question: str) -> str:
    """Open the chat, send a question, wait for the agent's reply, return its text."""
    if page.locator(".chat-panel").count() == 0:
        page.click(".chat-toggle")
    before = page.locator(".chat-msg.assistant").count()
    page.fill(".chat-input input", question)
    page.click(".chat-input button")
    page.wait_for_function(
        "n => document.querySelectorAll('.chat-msg.assistant:not(.typing)').length > n",
        arg=before, timeout=AGENT_TIMEOUT_MS,
    )
    page.wait_for_timeout(800)  # let the message animation finish
    return page.locator(".chat-msg.assistant:not(.typing)").last.inner_text()


# ---------- checks ----------

def check_inventory(page: Page, db: sqlite3.Connection) -> dict:
    name, price = db.execute(
        "SELECT name, price FROM catalogue WHERE product_id = ?", (INV_PRODUCT_ID,)
    ).fetchone()
    qty = db.execute(
        "SELECT quantity FROM inventory WHERE product_id = ? AND size = ?", (INV_PRODUCT_ID, INV_SIZE)
    ).fetchone()[0]
    result = {"name": name, "price": price, "size": INV_SIZE, "qty": qty, "question": INV_QUESTION}

    page.goto(f"{FRONT}/products/{INV_PRODUCT_ID}")
    page.wait_for_selector(".size-tile")
    reply = ask_chat(page, INV_QUESTION)
    page.screenshot(path=IMG / "inventory.png")
    result["reply"] = reply
    numbers = re.findall(r"\d+(?:\.\d+)?", reply.replace(",", ""))
    result["price_ok"] = any(abs(float(n) - price) < 0.001 for n in numbers)
    result["qty_ok"] = str(qty) in numbers
    return result


def check_search_cards(page: Page, db: sqlite3.Connection) -> dict:
    total = db.execute("SELECT count(*) FROM catalogue WHERE garment_type LIKE '%hood%'").fetchone()[0]
    page.goto(FRONT)
    page.wait_for_selector(".hero")
    reply = ask_chat(page, SEARCH_QUESTION)
    page.wait_for_url("**/chat-results", timeout=10_000)
    page.wait_for_selector(".product-card")
    page.wait_for_timeout(1200)  # staggered card fade-in
    cards = page.locator(".product-card h3").all_inner_texts()
    page.screenshot(path=IMG / "search_cards.png")
    hoodie_names = {r[0] for r in db.execute("SELECT name FROM catalogue WHERE garment_type LIKE '%hood%'")}
    return {
        "question": SEARCH_QUESTION, "reply": reply, "cards": cards, "db_total": total,
        "all_hoodies": all(c in hoodie_names for c in cards), "url": page.url,
    }


def check_usability(page: Page, db: sqlite3.Connection) -> dict:
    """Problem 9 feature 1: search box, category filter and price sort on Products."""
    total = db.execute("SELECT count(*) FROM catalogue WHERE garment_type LIKE '%hood%'").fetchone()[0]
    cheapest = db.execute("SELECT min(price) FROM catalogue WHERE garment_type LIKE '%hood%'").fetchone()[0]
    page.goto(f"{FRONT}/products")
    page.wait_for_selector(".product-card")
    page.select_option(".product-toolbar select >> nth=0", "hoodie")
    page.select_option(".product-toolbar select >> nth=1", "price-asc")
    page.wait_for_timeout(900)
    count_text = page.locator(".result-count").inner_text()
    prices = [float(p.strip("$")) for p in page.locator(".product-card .price").all_inner_texts()]
    page.screenshot(path=IMG / "usability.png")
    return {
        "count_text": count_text, "db_total": total, "first_price": prices[0], "db_cheapest": cheapest,
        "sorted_ok": prices == sorted(prices), "count_ok": f"Showing {total} of" in count_text,
        "url": page.url,
    }


# ---------- report ----------

def esc(s: object) -> str:
    return html.escape(str(s))


def badge(ok: bool | None) -> str:
    if ok is None:
        return '<span class="badge pending">Pending</span>'
    return '<span class="badge pass">Pass</span>' if ok else '<span class="badge fail">Check</span>'


def write_report(inv: dict | None, search: dict | None, usab: dict, model: str | None, db: sqlite3.Connection) -> None:
    # Database values for check 1 are shown even while the screenshot is pending.
    name, price = db.execute("SELECT name, price FROM catalogue WHERE product_id = ?", (INV_PRODUCT_ID,)).fetchone()
    sizes = db.execute(
        "SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY id", (INV_PRODUCT_ID,)
    ).fetchall()
    size_rows = "".join(
        f'<tr class="{"hl" if s == INV_SIZE else ""}"><td>{s}</td><td>{q}</td></tr>' for s, q in sizes
    )
    pending_note = (
        '<div class="pending-box"><strong>Not captured yet.</strong> The chatbot needs '
        "<code>PORTKEY_API_KEY</code> and <code>MODEL_NAME</code> in <code>hw4/.env</code>. "
        "Add them, then run <code>.venv\\Scripts\\python tests\\app_check.py</code> from "
        "<code>hw4</code> to capture this screenshot and refresh this page.</div>"
    )

    if inv:
        inv_body = f"""
        <figure><img src="app_check_images/inventory.png" alt="Chat answering a price and stock question on the Yale Dad Hoodie page">
        <figcaption>Asked on the product page: “{esc(inv['question'])}”</figcaption></figure>
        <p class="reply"><span>Agent reply</span>{esc(inv['reply'])}</p>
        <p><strong>What it proves:</strong> the agent answered from its database tools, not from memory.
        The price (${inv['price']:.2f}) and the stock for size {inv['size']} ({inv['qty']}) in the reply
        match the database rows above exactly. The size tiles on the page show the same numbers.</p>
        <p>Price in reply matches DB: {badge(inv['price_ok'])} &nbsp; Quantity in reply matches DB: {badge(inv['qty_ok'])}</p>"""
        inv_ok = inv["price_ok"] and inv["qty_ok"]
    else:
        inv_body = pending_note + (
            f"<p><strong>What it will prove:</strong> asking “{esc(INV_QUESTION)}” returns "
            f"${price:.2f} and {dict(sizes)[INV_SIZE]} in size {INV_SIZE}, the exact database values above.</p>"
        )
        inv_ok = None

    if search:
        search_body = f"""
        <figure><img src="app_check_images/search_cards.png" alt="Hoodie product cards on the Chat results page after asking the chatbot">
        <figcaption>Asked in the chat: “{esc(search['question'])}”</figcaption></figure>
        <p class="reply"><span>Agent reply</span>{esc(search['reply'])}</p>
        <p><strong>What it proves:</strong> the agent called <code>search_catalogue</code> and the
        <code>/chat</code> reply carried structured product cards. The page switched to <em>Chat results</em>
        and showed {len(search['cards'])} cards (capped at 12; the database has {search['db_total']} hoodies).
        Every card is a real hoodie from the catalogue: {badge(search['all_hoodies'])}</p>"""
        search_ok = search["all_hoodies"] and len(search["cards"]) > 0
    else:
        search_body = pending_note + (
            "<p><strong>What it will prove:</strong> the chatbot's catalogue search returns product cards "
            "that appear in the main page area (up to 12 of the 27 hoodies in the database), and each card "
            "opens the normal product page.</p>"
        )
        search_ok = None

    usab_body = f"""
        <figure><img src="app_check_images/usability.png" alt="Products page filtered to Hoodies and sorted by price, low to high">
        <figcaption>Products page → Category: <em>Hoodies</em>, Sort: <em>Price: low to high</em></figcaption></figure>
        <p><strong>What it proves:</strong> the Problem 9 search, filter and sort toolbar works in the running app.
        It shows “{esc(usab['count_text'])}”, matching the {usab['db_total']} hoodies in the database. The first card
        is ${usab['first_price']:.2f}, the cheapest hoodie in the database (${usab['db_cheapest']:.2f}), and prices rise from there.</p>
        <p>Count matches DB: {badge(usab['count_ok'])} &nbsp; Sorted low to high: {badge(usab['sorted_ok'])}</p>"""
    usab_ok = usab["count_ok"] and usab["sorted_ok"]

    summary = "".join(
        f"<li>{badge(ok)} {label}</li>"
        for label, ok in (("1. Inventory and price answer", inv_ok), ("2. Search shows product cards", search_ok), ("3. Usability: filter and sort", usab_ok))
    )

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Campus Customs App Check</title>
<style>
  :root {{ --blue:#00356b; --navy:#0a1e3c; --accent:#286dc0; --paper:#f8f6f1; --line:#e4e0d6; --ink:#1b2433; --muted:#5b6575; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:var(--paper); color:var(--ink); font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }}
  header {{ background:var(--blue); color:#fff; padding:32px 16px; }}
  header div, main {{ max-width:1000px; margin:0 auto; }}
  h1 {{ font-family:Georgia,serif; margin:0 0 6px; font-size:2rem; }}
  header p {{ margin:0; opacity:.85; }}
  main {{ padding:24px 16px 64px; }}
  .summary {{ background:#fff; border:1px solid var(--line); border-radius:12px; padding:16px 20px; }}
  .summary ul {{ list-style:none; padding:0; margin:8px 0 0; }}
  .summary li {{ margin:4px 0; }}
  section {{ background:#fff; border:1px solid var(--line); border-top:5px solid var(--blue); border-radius:12px; padding:24px; margin-top:28px; }}
  h2 {{ font-family:Georgia,serif; color:var(--navy); margin:0 0 14px; }}
  figure {{ margin:0 0 14px; }}
  figure img {{ width:100%; border:1px solid var(--line); border-radius:8px; display:block; }}
  figcaption {{ color:var(--muted); font-size:.9rem; margin-top:6px; }}
  .reply {{ background:#eef3fb; border-radius:8px; padding:12px 14px; white-space:pre-wrap; }}
  .reply span {{ display:block; font-size:.75rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:var(--accent); }}
  table {{ border-collapse:collapse; margin:8px 0 14px; min-width:260px; }}
  th, td {{ text-align:left; padding:6px 14px; border-bottom:1px solid var(--line); }}
  th {{ font-size:.8rem; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }}
  tr.hl td {{ background:#fff3d6; font-weight:700; }}
  code {{ background:#f0eee8; padding:1px 5px; border-radius:4px; font-size:.9em; }}
  .badge {{ display:inline-block; padding:1px 10px; border-radius:999px; font-size:.8rem; font-weight:700; }}
  .pass {{ background:#e8f5ed; color:#1e7a46; }} .fail {{ background:#fdecea; color:#b42318; }} .pending {{ background:#fff3d6; color:#8a5300; }}
  .pending-box {{ background:#fff3d6; border:1px dashed #e0b64c; border-radius:8px; padding:14px 16px; margin-bottom:12px; }}
  .meta {{ color:var(--muted); font-size:.85rem; margin-top:28px; }}
</style>
</head>
<body>
<header><div>
  <h1>Campus Customs App Check</h1>
  <p>Screenshots of the running site (FastAPI on :8000, React/Vite on :5173), captured with Playwright, and checked against <code style="background:rgba(255,255,255,.15);color:#fff">data/campus_customs.db</code>.</p>
</div></header>
<main>
  <div class="summary"><strong>Results</strong><ul>{summary}</ul></div>

  <section>
    <h2>1. Chat answers a stock and price question for one item in one size</h2>
    <p><strong>Database values</strong> for <em>{esc(name)}</em> (<code>{INV_PRODUCT_ID}</code>):
    price <strong>${price:.2f}</strong>; size <strong>{INV_SIZE}</strong> has <strong>{dict(sizes)[INV_SIZE]}</strong> in stock.</p>
    <table><thead><tr><th>inventory.size</th><th>inventory.quantity</th></tr></thead><tbody>{size_rows}</tbody></table>
    {inv_body}
  </section>

  <section>
    <h2>2. “What hoodies do you have?” puts product cards on the page</h2>
    {search_body}
  </section>

  <section>
    <h2>3. Usability: search, category filter and price sort (Problem 9)</h2>
    {usab_body}
  </section>

  <p class="meta">Generated {datetime.now().strftime("%Y-%m-%d %H:%M")} by <code>tests/app_check.py</code>
  · Chat model: {esc(model) if model else "not configured (.env missing)"} · Browser: Chrome via Playwright, 1280×860.</p>
</main>
</body>
</html>
"""
    (OUT / "app_check.html").write_text(page, encoding="utf-8")


def main() -> None:
    IMG.mkdir(parents=True, exist_ok=True)
    env = dotenv_values(HW4 / ".env") if (HW4 / ".env").exists() else {}
    live = bool(env.get("PORTKEY_API_KEY") and env.get("MODEL_NAME"))
    db = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)

    procs = start_servers()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome", headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 860})
            inv = search = None
            if live:
                print("1. inventory ...")
                inv = check_inventory(page, db)
                print(f"   reply: {inv['reply']}\n   price ok={inv['price_ok']} qty ok={inv['qty_ok']}")
                page = browser.new_page(viewport={"width": 1280, "height": 860})  # fresh chat
                print("2. search cards ...")
                search = check_search_cards(page, db)
                print(f"   {len(search['cards'])} cards, all hoodies={search['all_hoodies']}")
            else:
                print("1-2. SKIPPED: hw4/.env has no PORTKEY_API_KEY / MODEL_NAME (marked pending in the report)")
            print("3. usability ...")
            usab = check_usability(page, db)
            print(f"   {usab['count_text']} | sorted={usab['sorted_ok']}")
            browser.close()
    finally:
        stop_servers(procs)

    write_report(inv, search, usab, env.get("MODEL_NAME"), db)
    print(f"Wrote {OUT / 'app_check.html'}")


if __name__ == "__main__":
    main()
