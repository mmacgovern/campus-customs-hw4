"""The Campus Customs chat agent (PydanticAI, OpenAI model via Portkey).

Settings come from hw4/.env at run time:
    PORTKEY_API_KEY  Portkey API key (never printed or logged)
    MODEL_NAME       OpenAI 5.6 or 6 series model name as Portkey knows it
"""

import logging
import os
import re
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext, capture_run_messages
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from models import ChatDeps, ChatMessage, ChatReply
from tools import AGENT_TOOLS

BACKEND_DIR = Path(__file__).resolve().parent
PROMPT_PATH = BACKEND_DIR / "prompts" / "prompt.md"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# ---- Specs: limits for one chat message ----
MAX_REPLY_TOKENS = 800  # longest reply the model may write
MAX_MODEL_REQUESTS = 6  # agent steps: model calls per message (each tool round-trip is one)
MAX_TOOL_CALLS = 4  # tool calls per message across all steps
# (Search results are capped at MAX_SEARCH_RESULTS = 12 in models.py.)

load_dotenv(BACKEND_DIR.parent / ".env")
log = logging.getLogger("uvicorn.error")


class AgentNotConfigured(RuntimeError):
    """Raised when .env is missing PORTKEY_API_KEY or MODEL_NAME."""


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def make_model() -> OpenAIChatModel:
    api_key = os.getenv("PORTKEY_API_KEY")
    model_name = os.getenv("MODEL_NAME")
    if not api_key or not model_name:
        raise AgentNotConfigured("Set PORTKEY_API_KEY and MODEL_NAME in hw4/.env")
    if not re.search(r"gpt-(5\.6|6)", model_name):
        log.warning("MODEL_NAME %r is not an OpenAI 5.6 or 6 series model.", model_name)
    provider = OpenAIProvider(base_url=PORTKEY_BASE_URL, api_key=api_key)
    return OpenAIChatModel(model_name, provider=provider)


@lru_cache(maxsize=1)
def get_agent() -> Agent[ChatDeps, str]:
    """Build the agent once, on the first chat message."""
    agent = Agent(
        make_model(),
        deps_type=ChatDeps,
        output_type=str,
        instructions=load_prompt(),
        tools=AGENT_TOOLS,
        model_settings={"max_tokens": MAX_REPLY_TOKENS},
    )

    @agent.instructions
    def who_is_chatting(ctx: RunContext[ChatDeps]) -> str:
        d = ctx.deps
        if d.user_id is None:
            return "## Customer\nThe shopper is a guest (not signed in). Nothing from this chat is saved."
        return (
            "## Customer\n"
            "The shopper is signed in (identity verified by their login):\n"
            f"- First name: {d.first_name}\n"
            f"- Last name: {d.last_name}\n"
            f"- Email: {d.email}\n"
            "Earlier messages in this conversation are their saved chat history."
        )

    @agent.instructions
    def page_context(ctx: RunContext[ChatDeps]) -> str:
        d = ctx.deps
        if d.page_product_id:
            return (
                "## Page context\n"
                f"The shopper is viewing the product page for **{d.page_product_name}** "
                f'(product_id "{d.page_product_id}"). When they say "this", "it" or "this one" '
                "without naming another product, they mean this item: pass this product_id to the tools."
            )
        if d.page_path:
            return f"## Page context\nThe shopper is on the page {d.page_path!r}. No single product is on screen."
        return "## Page context\nUnknown page."

    return agent


def to_message_history(history: list[ChatMessage]) -> list[ModelMessage]:
    """Turn earlier turns (saved history or a guest's browser history) into PydanticAI messages."""
    messages: list[ModelMessage] = []
    for m in history:
        if m.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=m.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=m.content)]))
    return messages


async def run_chat(
    message: str,
    history: list[ChatMessage],
    deps: ChatDeps,
    trace: list[ModelMessage] | None = None,
) -> ChatReply:
    """Run one chat turn. `trace` receives this run's messages (also when the
    run fails or hits a limit) so the caller can write the audit trail."""
    with capture_run_messages() as messages:
        try:
            result = await get_agent().run(
                message,
                message_history=to_message_history(history),
                deps=deps,
                usage_limits=UsageLimits(
                    request_limit=MAX_MODEL_REQUESTS, tool_calls_limit=MAX_TOOL_CALLS
                ),
            )
        finally:
            if trace is not None:
                # Only this turn's new messages, not the replayed history.
                trace.extend(messages[len(history):])
    # Cards from this turn's catalogue search (empty if no search or no match).
    return ChatReply(reply=result.output, products=deps.search_results or [])
