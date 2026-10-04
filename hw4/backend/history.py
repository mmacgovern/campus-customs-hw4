"""Saved chat history for logged-in customers (the chat_history table).

Guests are never saved. Every query is parameterised and scoped to one user_id
taken from the login session.
"""

from contextlib import closing

from db import get_db
from models import ChatMessage, SavedChatMessage

# Messages reloaded into the chat panel, and earlier turns given to the agent.
PANEL_HISTORY_LIMIT = 50
AGENT_HISTORY_LIMIT = 20

SCHEMA = """
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_chat_history_user ON chat_history (user_id, id);
"""


def init_history_table() -> None:
    """Create the table on startup if it doesn't exist yet."""
    with closing(get_db(readonly=False)) as conn:
        conn.executescript(SCHEMA)


def save_turn(user_id: int, user_message: str, assistant_reply: str) -> None:
    """Save the customer's message and the assistant's reply together."""
    with closing(get_db(readonly=False)) as conn:
        conn.executemany(
            "INSERT INTO chat_history (user_id, role, message) VALUES (?, ?, ?)",
            [(user_id, "user", user_message), (user_id, "assistant", assistant_reply)],
        )
        conn.commit()


def load_recent(user_id: int, limit: int) -> list[SavedChatMessage]:
    """The user's last `limit` messages, oldest first."""
    with closing(get_db()) as conn:
        rows = conn.execute(
            "SELECT role, message, created_at FROM ("
            "  SELECT id, role, message, created_at FROM chat_history"
            "  WHERE user_id = ? ORDER BY id DESC LIMIT ?"
            ") ORDER BY id",
            (user_id, limit),
        ).fetchall()
    return [
        SavedChatMessage(role=r["role"], content=r["message"], created_at=r["created_at"])
        for r in rows
    ]


def agent_history(user_id: int) -> list[ChatMessage]:
    return [
        ChatMessage(role=m.role, content=m.content[:4000])
        for m in load_recent(user_id, AGENT_HISTORY_LIMIT)
    ]
