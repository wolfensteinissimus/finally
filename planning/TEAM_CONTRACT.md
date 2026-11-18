# Team Contract (module ownership & interfaces)

Read planning/PLAN.md first. Do NOT git commit. Only edit files in your own area. Need a change elsewhere? Say so in your final report.

## Ownership
| Role | Owns |
|---|---|
| Database Engineer | `backend/app/db/` (+ `backend/tests/db/`) |
| LLM Engineer | `backend/app/llm/` (+ `backend/tests/llm/`) |
| Backend Engineer | `backend/app/main.py`, `backend/app/api/`, `backend/app/services/`, `backend/pyproject.toml` deps, `backend/tests/api/`, `backend/tests/services/` (market code already done in `backend/app/market/`) |
| Frontend Engineer | `frontend/` |
| Deploy Engineer | `Dockerfile`, `docker-compose.yml`, `scripts/`, `.env.example`, `.gitignore`, `.dockerignore`, `db/.gitkeep` |
| Integration Tester | `test/` (Playwright E2E + docker-compose.test.yml) |

## Interfaces
**DB** (`app.db`, sqlite3 stdlib, path from env `DB_PATH` default `db/finally.db`; lazy `init_db()` creates schema + seeds; all funcs take optional `user_id="default"`; return plain dicts):
`init_db()`, `get_cash()`, `set_cash(v)`, `list_watchlist()->[ticker]`, `add_watchlist(t)->bool`, `remove_watchlist(t)->bool`, `list_positions()->[{ticker,quantity,avg_cost,updated_at}]`, `get_position(t)`, `upsert_position(t,qty,avg_cost)`, `delete_position(t)`, `insert_trade(t,side,qty,price)`, `list_trades(limit)`, `insert_snapshot(total_value)`, `list_snapshots(limit)`, `insert_chat_message(role,content,actions=None)`, `recent_chat_messages(limit=20)`, and atomic `execute_trade_tx(ticker, side, qty, price)` that updates cash+position+trade in one transaction and raises `ValueError` (message suitable for users) on insufficient cash/shares.

**LLM** (`app.llm`): `async def get_chat_response(message:str, portfolio:dict, history:list[dict]) -> ChatLLMResponse` (pydantic: `message:str`, `trades:list[TradeAction{ticker,side,quantity}]=[]`, `watchlist_changes:list[WatchlistChange{ticker,action}]=[]`). Honors `LLM_MOCK=true` (deterministic: e.g. message containing "buy" -> buys 1 AAPL; "add X" -> watchlist add; else generic reply). Uses cerebras skill (LiteLLM -> OpenRouter, gpt-oss-120b, Cerebras provider, structured outputs). Malformed output -> graceful fallback message, no exception.

**Backend** wires everything; endpoints exactly as PLAN.md section 8. JSON shapes (frontend relies on these):
- GET /api/portfolio -> `{cash, total_value, unrealized_pnl, positions:[{ticker,quantity,avg_cost,current_price,market_value,unrealized_pnl,pnl_pct}]}`
- POST /api/portfolio/trade `{ticker,quantity,side}` -> portfolio JSON above, 400 `{detail}` on validation error
- GET /api/portfolio/history -> `[{recorded_at,total_value}]`
- GET /api/watchlist -> `[{ticker,price,previous_price,change_pct}]`; POST `{ticker}`; DELETE /api/watchlist/{ticker}
- POST /api/chat `{message}` -> `{message, trades:[{ticker,side,quantity,price,status,error?}], watchlist_changes:[{ticker,action,status,error?}]}`
- GET /api/stream/prices SSE (existing `create_stream_router`), GET /api/health -> `{status:"ok"}`
- Static export served from `backend/static` (or `STATIC_DIR` env), SPA fallback to index.html. Snapshots every 30s + after each trade. Server runs `uvicorn app.main:app` from `backend/`.

**Frontend**: Next.js + TS + Tailwind, `output:'export'`, build output `frontend/out`. Dev proxy of /api to localhost:8000. Add `data-testid` attributes: `connection-status`, `header-total-value`, `header-cash`, `watchlist-row-{TICKER}`, `price-{TICKER}`, `trade-ticker`, `trade-quantity`, `trade-buy`, `trade-sell`, `positions-row-{TICKER}`, `chat-input`, `chat-send`, `chat-message`, `watchlist-add-input`, `watchlist-add-btn`, `watchlist-remove-{TICKER}`, `heatmap`, `pnl-chart`.

**Deploy**: Dockerfile per PLAN §11 (static copied to `/app/backend/static` or equivalent, db volume at `/app/db`, `DB_PATH=/app/db/finally.db`), scripts idempotent.
