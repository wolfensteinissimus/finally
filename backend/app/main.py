"""FinAlly FastAPI application."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from app import db
from app.api.routes import router as api_router
from app.market import PriceCache, create_market_data_source, create_stream_router
from app.services import portfolio as portfolio_svc
from app.services.state import AppState

logger = logging.getLogger(__name__)

SNAPSHOT_INTERVAL = 30.0


def static_dir() -> Path:
    env = os.environ.get("STATIC_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "static"


async def _snapshot_loop(cache: PriceCache, interval: float) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            portfolio_svc.record_snapshot(cache)
        except Exception:
            logger.exception("Snapshot failed")


def create_app() -> FastAPI:
    cache = PriceCache()
    source = create_market_data_source(cache)
    state = AppState(cache=cache, source=source)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db.init_db()
        tickers = list(db.list_watchlist())
        for p in db.list_positions():  # keep pricing held tickers
            if p["ticker"] not in tickers:
                tickers.append(p["ticker"])
        await source.start(tickers)
        task = asyncio.create_task(_snapshot_loop(cache, SNAPSHOT_INTERVAL))
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            await source.stop()

    app = FastAPI(title="FinAlly", lifespan=lifespan)
    app.state.app_state = state
    app.include_router(api_router)
    app.include_router(create_stream_router(cache))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        root = static_dir().resolve()
        if not root.is_dir():
            return JSONResponse({"detail": "Frontend not built"}, status_code=404)
        candidates = [full_path, f"{full_path}.html", f"{full_path}/index.html"]
        for c in candidates:
            if not c:
                continue
            p = (root / c).resolve()
            if p.is_file() and root in p.parents:
                return FileResponse(p)
        index = root / "index.html"
        if index.is_file():
            return FileResponse(index)
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    return app


app = create_app()
