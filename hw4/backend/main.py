"""Campus Customs API: products, stock, product images, accounts, and chat.

Run from the backend/ folder:
    uvicorn main:app --reload --port 8000
"""

import json
import logging
import os
import secrets
import sqlite3
import time
from contextlib import closing
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from pydantic_ai.exceptions import ModelHTTPError, UsageLimitExceeded
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import audit
import auth
from agent import AgentNotConfigured, run_chat
from db import IMAGES_DIR, get_db
import history
from tools import LOW_STOCK_THRESHOLD, category_of
from models import ChatDeps, ChatHistoryReply, ChatReply, ChatRequest

# Settings (secrets included) come from hw4/.env at run time.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="Campus Customs API")

# Allow the Vite dev server to call the API directly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Signed, HttpOnly session cookie that remembers who is logged in.
session_secret = os.getenv("SESSION_SECRET")
if not session_secret:
    logging.getLogger("uvicorn.error").warning(
        "SESSION_SECRET not set in .env; using a temporary one (logins reset on restart)."
    )
    session_secret = secrets.token_urlsafe(32)
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    session_cookie="cc_session",
    max_age=7 * 24 * 3600,
    same_site="lax",
)


# Validation errors normally echo the request body back; strip it so a
# password is never returned in an error response.
@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = sorted({str(e["loc"][-1]) for e in exc.errors()})
    return JSONResponse(
        status_code=422,
        content={"detail": f"Missing or invalid field(s): {', '.join(fields)}."},
    )


app.include_router(auth.router)

# Make sure the chat_history table exists.
history.init_history_table()

# Product images: catalogue.image_file_path is "products/<file>.jpg",
# so it maps to the URL /images/<file>.jpg.
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")


def product_from_row(row: sqlite3.Row) -> dict:
    image_name = Path(row["image_file_path"]).name
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "category": category_of(row["garment_type"]),
        "description": row["description"],
        "colors": json.loads(row["colors"]),
        "search_tags": json.loads(row["search_tags"]),
        "price": row["price"],
        "image_url": f"/images/{image_name}",
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/products")
def list_products() -> list[dict]:
    with closing(get_db()) as conn:
        rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
    return [product_from_row(r) for r in rows]


SIZE_ORDER = "CASE size WHEN 'XS' THEN 0 WHEN 'S' THEN 1 WHEN 'M' THEN 2 WHEN 'L' THEN 3 WHEN 'XL' THEN 4 WHEN 'XXL' THEN 5 ELSE 6 END"


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    with closing(get_db()) as conn:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        sizes = conn.execute(
            f"SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY {SIZE_ORDER}",
            (product_id,),
        ).fetchall()
    product = product_from_row(row)
    product["sizes"] = [
        {
            "size": s["size"],
            "quantity": s["quantity"],
            "low_stock": 0 < s["quantity"] <= LOW_STOCK_THRESHOLD,
        }
        for s in sizes
    ]
    return product


def page_product_name(product_id: str | None) -> str | None:
    """Name of the product on screen, or None if the ID isn't in the catalogue."""
    if not product_id:
        return None
    with closing(get_db()) as conn:
        row = conn.execute(
            "SELECT name FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
    return row["name"] if row else None


@app.get("/chat/history")
def chat_history(request: Request) -> ChatHistoryReply:
    """The signed-in customer's saved chat, for reloading the panel. Guests get []."""
    user = auth.current_user(request)
    if user is None:
        return ChatHistoryReply()
    return ChatHistoryReply(messages=history.load_recent(user["id"], history.PANEL_HISTORY_LIMIT))


# Sent when the model provider's safety filter blocks a message (for example
# a prompt-injection attempt). The safety layer worked, so answer politely
# instead of showing an error.
FILTERED_REPLY = (
    "Sorry, I can't help with that. I'm here to help you find Campus Customs gear: "
    "ask me about products, sizes, stock or prices!"
)


def is_content_filter(exc: ModelHTTPError) -> bool:
    text = str(exc.body).lower()
    return exc.status_code == 400 and ("content management policy" in text or "content_filter" in text)


LIMIT_REPLY = (
    "That question needed more steps than I'm allowed for one message. "
    "Could you ask about one product or one kind of item at a time?"
)


@app.post("/chat")
async def chat(body: ChatRequest, request: Request) -> ChatReply:
    started = time.perf_counter()
    # Identity comes only from the login session, never from the request body.
    user = auth.current_user(request)
    page = body.page
    product_name = page_product_name(page.product_id if page else None)
    deps = ChatDeps(
        user_id=user["id"] if user else None,
        first_name=user["first_name"] if user else None,
        last_name=user["last_name"] if user else None,
        email=user["email"] if user else None,
        page_path=page.path if page else None,
        page_product_id=page.product_id if product_name else None,
        page_product_name=product_name,
    )
    # Signed-in: use the saved history. Guest: use what the browser kept.
    earlier = history.agent_history(user["id"]) if user else body.history

    trace: list = []
    reply: ChatReply | None = None
    stop_reason = "completed"
    try:
        reply = await run_chat(body.message, earlier, deps, trace)
    except AgentNotConfigured:
        stop_reason = "not_configured"
        logging.getLogger("uvicorn.error").error("Chat is not configured: check hw4/.env.")
        raise HTTPException(503, "The shopping assistant isn't set up yet. Please try again later.")
    except ModelHTTPError as exc:
        if not is_content_filter(exc):
            stop_reason = f"error: {type(exc).__name__}"
            logging.getLogger("uvicorn.error").error("Chat failed: %s %s", type(exc).__name__, exc.status_code)
            raise HTTPException(502, "Sorry, the assistant is having trouble right now. Please try again.")
        stop_reason = "content_filter"
        reply = ChatReply(reply=FILTERED_REPLY, products=[])
    except UsageLimitExceeded as exc:
        # Hit the step or tool-call limit: answer politely instead of failing.
        stop_reason = "usage_limit: " + str(exc).split(". ")[0]
        reply = ChatReply(reply=LIMIT_REPLY, products=[])
    except Exception as exc:
        # Log only the error type: exception text can include request details.
        stop_reason = f"error: {type(exc).__name__}"
        logging.getLogger("uvicorn.error").error("Chat failed: %s", type(exc).__name__)
        raise HTTPException(502, "Sorry, the assistant is having trouble right now. Please try again.")
    finally:
        audit.append_entry({
            "time": audit.now(),
            "user": f"user:{user['id']}" if user else "guest",
            "page": {"path": page.path if page else None, "product_id": deps.page_product_id},
            "message": audit.short(body.message),
            "tool_calls": audit.tool_calls_from(trace),
            "model_requests": audit.model_requests_in(trace),
            "stop_reason": stop_reason,
            "finish_reason": audit.finish_reason_of(trace),
            "reply": audit.short(reply.reply) if reply else None,
            "cards_returned": len(reply.products) if reply else 0,
            "duration_ms": round((time.perf_counter() - started) * 1000),
        })

    if user:
        history.save_turn(user["id"], body.message, reply.reply)
    return reply
