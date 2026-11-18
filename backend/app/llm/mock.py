"""Deterministic mock LLM responses (LLM_MOCK=true)."""

import re

from .schema import ChatLLMResponse, TradeAction, WatchlistChange

_TICKER = r"([A-Za-z]{1,5})"


def mock_response(message: str) -> ChatLLMResponse:
    text = message.lower()
    m = re.search(r"\badd\s+" + _TICKER + r"\b", message, re.I)
    if m:
        t = m.group(1).upper()
        return ChatLLMResponse(
            message=f"Added {t} to your watchlist.",
            watchlist_changes=[WatchlistChange(ticker=t, action="add")],
        )
    m = re.search(r"\bremove\s+" + _TICKER + r"\b", message, re.I)
    if m:
        t = m.group(1).upper()
        return ChatLLMResponse(
            message=f"Removed {t} from your watchlist.",
            watchlist_changes=[WatchlistChange(ticker=t, action="remove")],
        )
    if "buy" in text:
        return ChatLLMResponse(
            message="Buying 1 share of AAPL for you.",
            trades=[TradeAction(ticker="AAPL", side="buy", quantity=1)],
        )
    if "sell" in text:
        return ChatLLMResponse(
            message="Selling 1 share of AAPL for you.",
            trades=[TradeAction(ticker="AAPL", side="sell", quantity=1)],
        )
    return ChatLLMResponse(
        message="This is a mock FinAlly response. Your portfolio looks balanced."
    )
