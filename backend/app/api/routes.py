"""REST routes (portfolio, watchlist, chat, health)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import db
from app.services import chat as chat_svc
from app.services import portfolio as portfolio_svc
from app.services import watchlist as watchlist_svc
from app.services.state import AppState

router = APIRouter(prefix="/api")


def _state(request: Request) -> AppState:
    return request.app.state.app_state


class TradeRequest(BaseModel):
    ticker: str
    quantity: float
    side: str


class WatchlistAddRequest(BaseModel):
    ticker: str


class ChatRequest(BaseModel):
    message: str


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/portfolio")
async def get_portfolio(request: Request) -> dict:
    return portfolio_svc.build_portfolio(_state(request).cache)


@router.post("/portfolio/trade")
async def post_trade(body: TradeRequest, request: Request) -> dict:
    cache = _state(request).cache
    try:
        portfolio_svc.execute_trade(cache, body.ticker, body.side, body.quantity)
    except portfolio_svc.TradeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return portfolio_svc.build_portfolio(cache)


@router.get("/portfolio/history")
async def get_history() -> list[dict]:
    snaps = db.list_snapshots(1000)
    out = [{"recorded_at": s["recorded_at"], "total_value": s["total_value"]} for s in snaps]
    out.sort(key=lambda s: s["recorded_at"])  # oldest first for charting
    return out


@router.get("/watchlist")
async def get_watchlist(request: Request) -> list[dict]:
    return watchlist_svc.list_watchlist(_state(request))


@router.post("/watchlist")
async def add_watchlist(body: WatchlistAddRequest, request: Request) -> list[dict]:
    state = _state(request)
    try:
        await watchlist_svc.add_ticker(state, body.ticker)
    except watchlist_svc.WatchlistError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return watchlist_svc.list_watchlist(state)


@router.delete("/watchlist/{ticker}")
async def delete_watchlist(ticker: str, request: Request) -> list[dict]:
    state = _state(request)
    try:
        await watchlist_svc.remove_ticker(state, ticker)
    except watchlist_svc.WatchlistError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return watchlist_svc.list_watchlist(state)


@router.post("/chat")
async def post_chat(body: ChatRequest, request: Request) -> dict:
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")
    return await chat_svc.handle_chat(_state(request), body.message)
