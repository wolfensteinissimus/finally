"""Portfolio service: valuation, trade execution, snapshots."""

from __future__ import annotations

import math

from app import db
from app.market import PriceCache


class TradeError(ValueError):
    """User-facing trade validation failure."""


def build_portfolio(cache: PriceCache) -> dict:
    """Current cash, positions with live P&L, and total value."""
    cash = float(db.get_cash())
    positions = []
    market_total = 0.0
    pnl_total = 0.0
    for pos in db.list_positions():
        qty = float(pos["quantity"])
        avg = float(pos["avg_cost"])
        price = cache.get_price(pos["ticker"])
        if price is None:
            price = avg  # no live price: value at cost
        mv = qty * price
        pnl = (price - avg) * qty
        pnl_pct = ((price - avg) / avg * 100.0) if avg else 0.0
        positions.append(
            {
                "ticker": pos["ticker"],
                "quantity": qty,
                "avg_cost": avg,
                "current_price": price,
                "market_value": mv,
                "unrealized_pnl": pnl,
                "pnl_pct": pnl_pct,
            }
        )
        market_total += mv
        pnl_total += pnl
    return {
        "cash": cash,
        "total_value": cash + market_total,
        "unrealized_pnl": pnl_total,
        "positions": positions,
    }


def record_snapshot(cache: PriceCache) -> None:
    db.insert_snapshot(build_portfolio(cache)["total_value"])


def execute_trade(cache: PriceCache, ticker: str, side: str, quantity: float) -> dict:
    """Validate and execute a market order. Returns {ticker, side, quantity, price}.

    Raises TradeError with a user-suitable message on any failure.
    """
    ticker = (ticker or "").strip().upper()
    side = (side or "").strip().lower()
    if not ticker:
        raise TradeError("Ticker is required")
    if side not in ("buy", "sell"):
        raise TradeError("Side must be 'buy' or 'sell'")
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise TradeError("Quantity must be a number") from None
    if not math.isfinite(quantity) or quantity <= 0:
        raise TradeError("Quantity must be greater than zero")
    price = cache.get_price(ticker)
    if price is None:
        raise TradeError(f"No live price available for {ticker}")
    try:
        db.execute_trade_tx(ticker, side, quantity, price)
    except ValueError as e:
        raise TradeError(str(e)) from None
    record_snapshot(cache)
    return {"ticker": ticker, "side": side, "quantity": quantity, "price": price}
