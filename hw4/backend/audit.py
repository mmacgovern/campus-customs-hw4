"""Append-only audit trail of agent activity: output/audit_trail.json.

The file is one JSON array, one entry per chat turn. New entries are added by
replacing the closing "]" at the end of the file, so earlier bytes are never
rewritten and the file stays valid JSON. If the file is not a JSON array we
refuse to touch it rather than risk clobbering it.

Nothing secret is written: user identity is the numeric user_id only, every
string is shortened, and anything that looks like a password, password hash
or API key is redacted.
"""

import json
import logging
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    RetryPromptPart,
    ToolCallPart,
    ToolReturnPart,
)

# Tests can point this at a scratch file via CC_AUDIT_PATH.
AUDIT_PATH = Path(
    os.getenv("CC_AUDIT_PATH")
    or Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
)
SHORT = 160  # max characters for any logged string
_lock = threading.Lock()
log = logging.getLogger("uvicorn.error")

_REDACTIONS = [
    (re.compile(r"pbkdf2_sha256\$\S+"), "[redacted-hash]"),
    (re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9_\-]{12,}"), "[redacted-key]"),
    (re.compile(r"(?i)(password|passwd|pwd|api[_ ]?key|secret|token)(\s*(?:is|:|=)\s*)\S+"), r"\1\2[redacted]"),
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def redact(text: str) -> str:
    for pattern, repl in _REDACTIONS:
        text = pattern.sub(repl, text)
    for name in ("PORTKEY_API_KEY", "SESSION_SECRET"):
        value = os.getenv(name)
        if value and len(value) >= 8:
            text = text.replace(value, "[redacted-key]")
    return text


def short(value: Any, limit: int = SHORT) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)
    text = redact(" ".join(text.split()))
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _short_result(content: Any) -> str:
    # Our tools return Pydantic models with a plain-English `message`; log that
    # plus a couple of counts instead of the whole payload.
    message = getattr(content, "message", None)
    if message is None:
        return short(content)
    extras = []
    for field in ("found", "total_matches"):
        if hasattr(content, field):
            extras.append(f"{field}={getattr(content, field)}")
    products = getattr(content, "products", None)
    if products is not None:
        extras.append(f"cards={len(products)}")
    return short(f"{message} ({', '.join(extras)})" if extras else message)


def tool_calls_from(messages: list[ModelMessage]) -> list[dict]:
    """One record per tool call: time, tool, short args, short result."""
    calls: dict[str, dict] = {}
    order: list[str] = []
    for msg in messages:
        for part in msg.parts:
            if isinstance(part, ToolCallPart):
                calls[part.tool_call_id] = {
                    "time": msg.timestamp.isoformat(timespec="milliseconds") if isinstance(msg, ModelResponse) else now(),
                    "tool": part.tool_name,
                    "args": short(part.args_as_dict()),
                    "result": "(no result: run stopped)",
                }
                order.append(part.tool_call_id)
            elif isinstance(part, ToolReturnPart) and part.tool_call_id in calls:
                calls[part.tool_call_id]["time"] = part.timestamp.isoformat(timespec="milliseconds")
                calls[part.tool_call_id]["result"] = _short_result(part.content)
            elif isinstance(part, RetryPromptPart) and part.tool_call_id in calls:
                calls[part.tool_call_id]["result"] = "retry: " + short(part.model_response())
    return [calls[i] for i in order]


def model_requests_in(messages: list[ModelMessage]) -> int:
    return sum(isinstance(m, ModelResponse) for m in messages)


def finish_reason_of(messages: list[ModelMessage]) -> str | None:
    responses = [m for m in messages if isinstance(m, ModelResponse)]
    return getattr(responses[-1], "finish_reason", None) if responses else None


def append_entry(entry: dict) -> None:
    """Append one entry; an audit failure is logged but never breaks the chat."""
    try:
        _append(entry)
    except OSError as exc:
        log.error("Could not write audit trail: %s", type(exc).__name__)


def _append(entry: dict) -> None:
    """Append one entry to the JSON array without rewriting earlier entries."""
    data = json.dumps(entry, ensure_ascii=False, indent=2)
    data = "\n".join("  " + line for line in data.splitlines())
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not AUDIT_PATH.exists() or AUDIT_PATH.stat().st_size == 0:
            AUDIT_PATH.write_text(f"[\n{data}\n]\n", encoding="utf-8")
            return
        with open(AUDIT_PATH, "r+b") as f:
            # Find the final "]" (skipping trailing whitespace).
            f.seek(0, os.SEEK_END)
            pos = f.tell()
            while pos > 0:
                pos -= 1
                f.seek(pos)
                ch = f.read(1)
                if not ch.isspace():
                    break
            if ch != b"]":
                log.error("Audit trail is not a JSON array; not writing to it.")
                return
            # Is the array empty ("[ ]")? Then no comma is needed.
            f.seek(0)
            empty = f.read(pos).strip() == b"["
            f.seek(pos)
            f.truncate()
            f.write((("\n" if empty else ",\n") + data + "\n]\n").encode("utf-8"))
