"""SQLite repository functions.

The DB path comes from env ``DB_PATH`` (default ``db/finally.db``), read on every call.
The schema is created and seeded lazily the first time a given path is used (and again
if the file disappears). All functions take an optional ``user_id`` and return plain
dicts / lists.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_USER = "default"
INITIAL_CASH = 10000.0
DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")
_EPS = 1e-9

_init_lock = threading.Lock()
_initialized: set[str] = set()


def get_db_path() -> str:
    return os.environ.get("DB_PATH") or "db/finally.db"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _id() -> str:
    return str(uuid.uuid4())


def _norm(ticker: str) -> str:
    return ticker.strip().upper()


def _open(path: str) -> sqlite3.Connection:
    # isolation_level=None -> we manage transactions explicitly.
    conn = sqlite3.connect(path, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def init_db() -> None:
    """Create schema and seed default data if needed. Idempotent."""
    path = get_db_path()
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = _open(path)
    try:
        try:
            conn.execute("PRAGMA journal_mode = WAL")
        except sqlite3.DatabaseError:
            pass
        conn.executescript(_SCHEMA_PATH.read_text())
        conn.execute("BEGIN IMMEDIATE")
        try:
            now = _now()
            conn.execute(
                "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
                (DEFAULT_USER, INITIAL_CASH, now),
            )
            # Seed the watchlist only for a brand-new default user (no watchlist rows and
            # no prior trades/positions means fresh DB); don't resurrect removed tickers.
            fresh = conn.execute(
                "SELECT COUNT(*) FROM watchlist WHERE user_id = ?", (DEFAULT_USER,)
            ).fetchone()[0] == 0 and conn.execute(
                "SELECT COUNT(*) FROM trades WHERE user_id = ?", (DEFAULT_USER,)
            ).fetchone()[0] == 0 and conn.execute(
                "SELECT COUNT(*) FROM chat_messages WHERE user_id = ?", (DEFAULT_USER,)
            ).fetchone()[0] == 0
            if fresh:
                conn.executemany(
                    "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                    [(_id(), DEFAULT_USER, t, now) for t in DEFAULT_TICKERS],
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    with _init_lock:
        _initialized.add(path)


def _ensure_init(path: str) -> None:
    if path == ":memory:":
        return
    if path in _initialized and os.path.exists(path):
        return
    init_db()


@contextmanager
def _conn(write: bool = False):
    """Yield a connection; if ``write``, wrap in an IMMEDIATE transaction."""
    path = get_db_path()
    _ensure_init(path)
    conn = _open(path)
    try:
        if write:
            conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
            if write:
                conn.execute("COMMIT")
        except BaseException:
            if write and conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()


def _ensure_user(conn: sqlite3.Connection, user_id: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
        (user_id, INITIAL_CASH, _now()),
    )


# ---------------------------------------------------------------- cash

def get_cash(user_id: str = DEFAULT_USER) -> float:
    with _conn(write=user_id != DEFAULT_USER) as c:
        if user_id != DEFAULT_USER:
            _ensure_user(c, user_id)
        row = c.execute("SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)).fetchone()
        return float(row["cash_balance"]) if row else INITIAL_CASH


def set_cash(value: float, user_id: str = DEFAULT_USER) -> None:
    with _conn(write=True) as c:
        _ensure_user(c, user_id)
        c.execute("UPDATE users_profile SET cash_balance = ? WHERE id = ?", (float(value), user_id))


# ----------------------------------------------------------- watchlist

def list_watchlist(user_id: str = DEFAULT_USER) -> list[str]:
    with _conn() as c:
        rows = c.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at, rowid", (user_id,)
        ).fetchall()
        return [r["ticker"] for r in rows]


def add_watchlist(ticker: str, user_id: str = DEFAULT_USER) -> bool:
    """Add a ticker. Returns False if it was already present."""
    t = _norm(ticker)
    with _conn(write=True) as c:
        cur = c.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (_id(), user_id, t, _now()),
        )
        return cur.rowcount > 0


def remove_watchlist(ticker: str, user_id: str = DEFAULT_USER) -> bool:
    """Remove a ticker. Returns False if it was not present."""
    with _conn(write=True) as c:
        cur = c.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, _norm(ticker))
        )
        return cur.rowcount > 0


# ----------------------------------------------------------- positions

_POS_COLS = "ticker, quantity, avg_cost, updated_at"


def list_positions(user_id: str = DEFAULT_USER) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            f"SELECT {_POS_COLS} FROM positions WHERE user_id = ? ORDER BY ticker", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_position(ticker: str, user_id: str = DEFAULT_USER) -> dict | None:
    with _conn() as c:
        row = c.execute(
            f"SELECT {_POS_COLS} FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, _norm(ticker)),
        ).fetchone()
        return dict(row) if row else None


def _upsert_position(c, ticker, qty, avg_cost, user_id):
    c.execute(
        """INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT (user_id, ticker) DO UPDATE SET
             quantity = excluded.quantity,
             avg_cost = excluded.avg_cost,
             updated_at = excluded.updated_at""",
        (_id(), user_id, ticker, float(qty), float(avg_cost), _now()),
    )


def upsert_position(ticker: str, quantity: float, avg_cost: float, user_id: str = DEFAULT_USER) -> None:
    with _conn(write=True) as c:
        _upsert_position(c, _norm(ticker), quantity, avg_cost, user_id)


def delete_position(ticker: str, user_id: str = DEFAULT_USER) -> bool:
    with _conn(write=True) as c:
        cur = c.execute(
            "DELETE FROM positions WHERE user_id = ? AND ticker = ?", (user_id, _norm(ticker))
        )
        return cur.rowcount > 0


# -------------------------------------------------------------- trades

def _insert_trade(c, ticker, side, qty, price, user_id) -> dict:
    row = {
        "id": _id(),
        "ticker": ticker,
        "side": side,
        "quantity": float(qty),
        "price": float(price),
        "executed_at": _now(),
    }
    c.execute(
        "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (row["id"], user_id, ticker, side, row["quantity"], row["price"], row["executed_at"]),
    )
    return row


def insert_trade(ticker: str, side: str, quantity: float, price: float,
                 user_id: str = DEFAULT_USER) -> dict:
    if side not in ("buy", "sell"):
        raise ValueError("Side must be 'buy' or 'sell'.")
    with _conn(write=True) as c:
        return _insert_trade(c, _norm(ticker), side, quantity, price, user_id)


def list_trades(limit: int = 100, user_id: str = DEFAULT_USER) -> list[dict]:
    """Most recent trades first."""
    with _conn() as c:
        rows = c.execute(
            "SELECT id, ticker, side, quantity, price, executed_at FROM trades "
            "WHERE user_id = ? ORDER BY executed_at DESC, rowid DESC LIMIT ?",
            (user_id, int(limit)),
        ).fetchall()
        return [dict(r) for r in rows]


def execute_trade_tx(ticker: str, side: str, qty: float, price: float,
                     user_id: str = DEFAULT_USER) -> dict:
    """Atomically apply a market trade: cash + position + trade row in one transaction.

    Raises ValueError with a user-presentable message on invalid input, insufficient
    cash, or insufficient shares (nothing is changed in that case).
    Returns ``{ticker, side, quantity, price, cash, position}`` where ``position`` is the
    resulting position dict or None if fully closed.
    """
    t = _norm(ticker)
    side = str(side).lower()
    if not t:
        raise ValueError("Ticker is required.")
    if side not in ("buy", "sell"):
        raise ValueError("Side must be 'buy' or 'sell'.")
    try:
        qty = float(qty)
        price = float(price)
    except (TypeError, ValueError):
        raise ValueError("Quantity and price must be numbers.") from None
    if not (qty > 0) or qty == float("inf"):
        raise ValueError("Quantity must be greater than zero.")
    if not (price > 0) or price == float("inf"):
        raise ValueError(f"No valid price available for {t}.")

    with _conn(write=True) as c:
        _ensure_user(c, user_id)
        cash = float(c.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)).fetchone()[0])
        pos = c.execute(
            "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, t),
        ).fetchone()
        cur_qty = float(pos["quantity"]) if pos else 0.0
        cur_avg = float(pos["avg_cost"]) if pos else 0.0
        cost = qty * price

        if side == "buy":
            if cost > cash + _EPS:
                raise ValueError(
                    f"Insufficient cash: need ${cost:,.2f} but only ${cash:,.2f} available."
                )
            new_qty = cur_qty + qty
            new_avg = (cur_qty * cur_avg + cost) / new_qty
            new_cash = max(cash - cost, 0.0)
        else:
            if qty > cur_qty + _EPS:
                raise ValueError(
                    f"Insufficient shares: trying to sell {qty:g} {t} but only {cur_qty:g} owned."
                )
            new_qty = cur_qty - qty
            new_avg = cur_avg
            new_cash = cash + cost
            if new_qty <= _EPS:
                new_qty = 0.0

        c.execute("UPDATE users_profile SET cash_balance = ? WHERE id = ?", (new_cash, user_id))
        if new_qty == 0.0:
            c.execute("DELETE FROM positions WHERE user_id = ? AND ticker = ?", (user_id, t))
            position = None
        else:
            _upsert_position(c, t, new_qty, new_avg, user_id)
            position = {"ticker": t, "quantity": new_qty, "avg_cost": new_avg}
        trade = _insert_trade(c, t, side, qty, price, user_id)

    return {
        "ticker": t, "side": side, "quantity": qty, "price": price,
        "cash": new_cash, "position": position, "trade_id": trade["id"],
        "executed_at": trade["executed_at"],
    }


# ----------------------------------------------------------- snapshots

def insert_snapshot(total_value: float, user_id: str = DEFAULT_USER) -> dict:
    row = {"recorded_at": _now(), "total_value": float(total_value)}
    with _conn(write=True) as c:
        c.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (_id(), user_id, row["total_value"], row["recorded_at"]),
        )
    return row


def list_snapshots(limit: int = 1000, user_id: str = DEFAULT_USER) -> list[dict]:
    """The most recent ``limit`` snapshots, in chronological (ascending) order."""
    with _conn() as c:
        rows = c.execute(
            "SELECT recorded_at, total_value FROM ("
            " SELECT recorded_at, total_value, rowid AS rid FROM portfolio_snapshots"
            " WHERE user_id = ? ORDER BY recorded_at DESC, rowid DESC LIMIT ?"
            ") ORDER BY recorded_at ASC, rid ASC",
            (user_id, int(limit)),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------- chat

def insert_chat_message(role: str, content: str, actions: dict | list | None = None,
                        user_id: str = DEFAULT_USER) -> dict:
    if role not in ("user", "assistant"):
        raise ValueError("Role must be 'user' or 'assistant'.")
    row = {"id": _id(), "role": role, "content": content, "actions": actions,
           "created_at": _now()}
    with _conn(write=True) as c:
        c.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (row["id"], user_id, role, content,
             None if actions is None else json.dumps(actions), row["created_at"]),
        )
    return row


def recent_chat_messages(limit: int = 20, user_id: str = DEFAULT_USER) -> list[dict]:
    """The most recent ``limit`` messages, oldest first. ``actions`` is decoded JSON or None."""
    with _conn() as c:
        rows = c.execute(
            "SELECT role, content, actions, created_at FROM ("
            " SELECT role, content, actions, created_at, rowid AS rid FROM chat_messages"
            " WHERE user_id = ? ORDER BY created_at DESC, rowid DESC LIMIT ?"
            ") ORDER BY created_at ASC, rid ASC",
            (user_id, int(limit)),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["actions"] = json.loads(d["actions"]) if d["actions"] else None
        out.append(d)
    return out
