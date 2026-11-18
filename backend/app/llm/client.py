"""LLM client: LiteLLM -> OpenRouter -> Cerebras (gpt-oss-120b) with structured outputs."""

import logging
import os

from litellm import acompletion
from pydantic import ValidationError

from .mock import mock_response
from .prompts import build_messages
from .schema import ChatLLMResponse

logger = logging.getLogger(__name__)

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

FALLBACK_MESSAGE = "Sorry, I had trouble processing that request. Please try again."


def _mock_enabled() -> bool:
    return os.environ.get("LLM_MOCK", "").strip().lower() == "true"


def parse_response(content: str | None) -> ChatLLMResponse:
    """Parse model output; never raises."""
    if not content:
        return ChatLLMResponse(message=FALLBACK_MESSAGE)
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return ChatLLMResponse.model_validate_json(text)
    except ValidationError:
        pass
    # Try the outermost JSON object embedded in surrounding text.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return ChatLLMResponse.model_validate_json(text[start : end + 1])
        except ValidationError:
            pass
    logger.warning("Malformed LLM output: %r", content[:200])
    return ChatLLMResponse(message=FALLBACK_MESSAGE)


async def get_chat_response(message: str, portfolio: dict, history: list[dict]) -> ChatLLMResponse:
    if _mock_enabled():
        return mock_response(message)
    try:
        messages = build_messages(message, portfolio, history)
        response = await acompletion(
            model=MODEL,
            messages=messages,
            response_format=ChatLLMResponse,
            reasoning_effort="low",
            extra_body=EXTRA_BODY,
        )
        content = response.choices[0].message.content
    except Exception:
        logger.exception("LLM call failed")
        return ChatLLMResponse(message=FALLBACK_MESSAGE)
    return parse_response(content)
