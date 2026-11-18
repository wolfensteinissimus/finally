"""Watchlist service: DB + market data source sync."""

from __future__ import annotations

import re

from app import db
from app.services.state import AppState

TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


class WatchlistError(ValueError):
    pass


def normalize_ticker(ticker: str) -> str:
    t = (ticker or "").strip().upper()
    if not TICKER_RE.match(t):
        raise WatchlistError(f"Invalid ticker: {ticker!r}")
    return t


def list_watchlist(state: AppState) -> list[dict]:
    out = []
    for t in db.list_watchlist():
        u = state.cache.get(t)
        out.append(
            {
                "ticker": t,
                "price": u.price if u else None,
                "previous_price": u.previous_price if u else None,
                "change_pct": u.change_percent if u else None,
            }
        )
    return out


async def add_ticker(state: AppState, ticker: str) -> str:
    t = normalize_ticker(ticker)
    db.add_watchlist(t)  # idempotent
    await state.source.add_ticker(t)
    return t


async def remove_ticker(state: AppState, ticker: str) -> str:
    t = normalize_ticker(ticker)
    db.remove_watchlist(t)
    # Keep pricing a ticker we still hold so portfolio valuation stays live.
    if not db.get_position(t):
        await state.source.remove_ticker(t)
    return t
