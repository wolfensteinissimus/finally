"""Chat orchestration: context -> LLM -> auto-execute -> persist."""

from __future__ import annotations

import logging

from app import db, llm
from app.services import portfolio as portfolio_svc
from app.services import watchlist as watchlist_svc
from app.services.state import AppState

logger = logging.getLogger(__name__)


def _context(state: AppState) -> dict:
    ctx = portfolio_svc.build_portfolio(state.cache)
    ctx["watchlist"] = watchlist_svc.list_watchlist(state)
    return ctx


async def handle_chat(state: AppState, message: str) -> dict:
    ctx = _context(state)
    history = [
        {"role": m["role"], "content": m["content"]} for m in db.recent_chat_messages(20)
    ]
    db.insert_chat_message("user", message)

    try:
        resp = await llm.get_chat_response(message, ctx, history)
    except Exception:  # LLM layer should not raise, but never 500 the chat
        logger.exception("LLM call failed")
        text = "Sorry, I couldn't reach the AI service. Please try again."
        db.insert_chat_message("assistant", text, {"trades": [], "watchlist_changes": []})
        return {"message": text, "trades": [], "watchlist_changes": []}

    trade_results = []
    for tr in resp.trades:
        entry = {"ticker": tr.ticker.upper(), "side": tr.side, "quantity": tr.quantity}
        try:
            done = portfolio_svc.execute_trade(state.cache, tr.ticker, tr.side, tr.quantity)
            entry.update(done)
            entry["status"] = "executed"
        except portfolio_svc.TradeError as e:
            entry.update(price=None, status="failed", error=str(e))
        trade_results.append(entry)

    wl_results = []
    for ch in resp.watchlist_changes:
        entry = {"ticker": ch.ticker.upper(), "action": ch.action}
        try:
            if ch.action == "add":
                entry["ticker"] = await watchlist_svc.add_ticker(state, ch.ticker)
            elif ch.action == "remove":
                entry["ticker"] = await watchlist_svc.remove_ticker(state, ch.ticker)
            else:
                raise watchlist_svc.WatchlistError(f"Unknown action: {ch.action}")
            entry["status"] = "executed"
        except watchlist_svc.WatchlistError as e:
            entry.update(status="failed", error=str(e))
        wl_results.append(entry)

    # Make failures visible in the text even if the LLM claimed success.
    text = resp.message
    errors = [f"{t['side']} {t['quantity']:g} {t['ticker']}: {t['error']}"
              for t in trade_results if t["status"] == "failed"]
    errors += [f"watchlist {w['action']} {w['ticker']}: {w['error']}"
               for w in wl_results if w["status"] == "failed"]
    if errors:
        text += "\n\nCould not complete: " + "; ".join(errors)

    db.insert_chat_message(
        "assistant", text, {"trades": trade_results, "watchlist_changes": wl_results}
    )
    return {"message": text, "trades": trade_results, "watchlist_changes": wl_results}
