import sqlite3
import threading

import pytest

from app import db


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    path = tmp_path / "sub" / "finally.db"
    monkeypatch.setenv("DB_PATH", str(path))
    return path


def test_lazy_init_creates_file_and_seeds(tmp_db):
    assert not tmp_db.exists()
    assert db.get_cash() == 10000.0
    assert tmp_db.exists()
    assert db.list_watchlist() == db.DEFAULT_TICKERS
    assert len(db.list_watchlist()) == 10


def test_init_idempotent_no_reseed_after_removal():
    db.init_db()
    db.remove_watchlist("AAPL")
    db.set_cash(5.0)
    db.init_db()
    assert "AAPL" not in db.list_watchlist()
    assert db.get_cash() == 5.0


def test_reinit_if_file_deleted(tmp_db):
    db.get_cash()
    tmp_db.unlink()
    for ext in ("-wal", "-shm"):
        p = tmp_db.with_name(tmp_db.name + ext)
        if p.exists():
            p.unlink()
    assert db.get_cash() == 10000.0
    assert len(db.list_watchlist()) == 10


def test_tables_exist(tmp_db):
    db.init_db()
    conn = sqlite3.connect(tmp_db)
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert {"users_profile", "watchlist", "positions", "trades",
            "portfolio_snapshots", "chat_messages"} <= names


def test_cash():
    db.set_cash(1234.56)
    assert db.get_cash() == 1234.56


def test_watchlist_add_remove():
    assert db.add_watchlist("pypl") is True
    assert db.add_watchlist("PYPL") is False
    assert db.list_watchlist()[-1] == "PYPL"
    assert db.remove_watchlist("pypl") is True
    assert db.remove_watchlist("PYPL") is False
    assert "PYPL" not in db.list_watchlist()


def test_position_crud():
    assert db.get_position("AAPL") is None
    db.upsert_position("aapl", 5, 100.0)
    p = db.get_position("AAPL")
    assert p["ticker"] == "AAPL" and p["quantity"] == 5 and p["avg_cost"] == 100.0
    assert "updated_at" in p
    db.upsert_position("AAPL", 7.5, 110.0)
    assert len(db.list_positions()) == 1
    assert db.get_position("AAPL")["quantity"] == 7.5
    assert db.delete_position("AAPL") is True
    assert db.delete_position("AAPL") is False
    assert db.list_positions() == []


def test_list_positions_shape():
    db.upsert_position("MSFT", 1, 1)
    db.upsert_position("AAPL", 1, 1)
    rows = db.list_positions()
    assert [r["ticker"] for r in rows] == ["AAPL", "MSFT"]
    assert set(rows[0]) == {"ticker", "quantity", "avg_cost", "updated_at"}


def test_trades_and_limit_order():
    for i in range(5):
        db.insert_trade("AAPL", "buy", i + 1, 10.0)
    rows = db.list_trades(3)
    assert len(rows) == 3
    assert [r["quantity"] for r in rows] == [5, 4, 3]
    with pytest.raises(ValueError):
        db.insert_trade("AAPL", "hold", 1, 1)


def test_snapshots_chronological_and_limit():
    for v in (1, 2, 3, 4):
        db.insert_snapshot(float(v))
    rows = db.list_snapshots(3)
    assert [r["total_value"] for r in rows] == [2.0, 3.0, 4.0]
    assert set(rows[0]) == {"recorded_at", "total_value"}


def test_chat_messages_roundtrip():
    db.insert_chat_message("user", "hi")
    db.insert_chat_message("assistant", "yo", {"trades": [{"ticker": "AAPL"}]})
    for i in range(3):
        db.insert_chat_message("user", f"m{i}")
    msgs = db.recent_chat_messages(4)
    assert [m["content"] for m in msgs] == ["yo", "m0", "m1", "m2"]
    assert msgs[0]["actions"] == {"trades": [{"ticker": "AAPL"}]}
    assert msgs[1]["actions"] is None
    assert len(db.recent_chat_messages()) == 5
    with pytest.raises(ValueError):
        db.insert_chat_message("system", "x")


def test_user_isolation():
    db.add_watchlist("ZZZ", user_id="bob")
    db.upsert_position("ZZZ", 1, 1, user_id="bob")
    db.insert_snapshot(5.0, user_id="bob")
    db.insert_chat_message("user", "hey", user_id="bob")
    assert db.get_cash("bob") == 10000.0
    assert db.list_watchlist("bob") == ["ZZZ"]
    assert "ZZZ" not in db.list_watchlist()
    assert db.list_positions() == []
    assert db.list_snapshots() == []
    assert db.recent_chat_messages() == []
    db.execute_trade_tx("AAPL", "buy", 1, 100, user_id="bob")
    assert db.get_cash("bob") == 9900.0
    assert db.get_cash() == 10000.0


# ------------------------------------------------------------ execute_trade_tx

def test_buy_new_position():
    r = db.execute_trade_tx("aapl", "buy", 10, 190.0)
    assert db.get_cash() == pytest.approx(10000 - 1900)
    p = db.get_position("AAPL")
    assert p["quantity"] == 10 and p["avg_cost"] == 190.0
    assert r["cash"] == pytest.approx(8100)
    assert r["position"]["quantity"] == 10
    t = db.list_trades()
    assert len(t) == 1 and t[0]["side"] == "buy" and t[0]["price"] == 190.0


def test_buy_weighted_avg_cost():
    db.execute_trade_tx("AAPL", "buy", 10, 100.0)
    db.execute_trade_tx("AAPL", "buy", 10, 200.0)
    p = db.get_position("AAPL")
    assert p["quantity"] == 20
    assert p["avg_cost"] == pytest.approx(150.0)


def test_fractional_shares():
    db.execute_trade_tx("AAPL", "buy", 0.5, 200.0)
    assert db.get_position("AAPL")["quantity"] == 0.5
    assert db.get_cash() == pytest.approx(9900)


def test_partial_sell_keeps_avg_cost():
    db.execute_trade_tx("AAPL", "buy", 10, 100.0)
    r = db.execute_trade_tx("AAPL", "sell", 4, 150.0)
    p = db.get_position("AAPL")
    assert p["quantity"] == 6 and p["avg_cost"] == 100.0
    assert db.get_cash() == pytest.approx(10000 - 1000 + 600)
    assert r["position"]["quantity"] == 6


def test_full_sell_deletes_position():
    db.execute_trade_tx("AAPL", "buy", 10, 100.0)
    r = db.execute_trade_tx("AAPL", "sell", 10, 90.0)
    assert db.get_position("AAPL") is None
    assert r["position"] is None
    assert db.get_cash() == pytest.approx(9900)
    assert len(db.list_trades()) == 2


def test_sell_fractional_residual_float_error_closes_position():
    for _ in range(3):
        db.execute_trade_tx("AAPL", "buy", 0.1, 10.0)
    db.execute_trade_tx("AAPL", "sell", 0.3, 10.0)
    assert db.get_position("AAPL") is None


def test_insufficient_cash_changes_nothing():
    with pytest.raises(ValueError, match="Insufficient cash"):
        db.execute_trade_tx("AAPL", "buy", 100, 200.0)
    assert db.get_cash() == 10000.0
    assert db.list_positions() == []
    assert db.list_trades() == []


def test_buy_exact_cash_allowed():
    db.execute_trade_tx("AAPL", "buy", 100, 100.0)
    assert db.get_cash() == 0.0


def test_insufficient_shares_changes_nothing():
    with pytest.raises(ValueError, match="Insufficient shares"):
        db.execute_trade_tx("AAPL", "sell", 1, 100.0)
    db.execute_trade_tx("AAPL", "buy", 2, 100.0)
    with pytest.raises(ValueError, match="Insufficient shares"):
        db.execute_trade_tx("AAPL", "sell", 3, 100.0)
    assert db.get_position("AAPL")["quantity"] == 2
    assert db.get_cash() == pytest.approx(9800)
    assert len(db.list_trades()) == 1


@pytest.mark.parametrize("ticker,side,qty,price", [
    ("AAPL", "buy", 0, 10),
    ("AAPL", "buy", -1, 10),
    ("AAPL", "buy", float("nan"), 10),
    ("AAPL", "buy", 1, 0),
    ("AAPL", "buy", 1, -5),
    ("AAPL", "short", 1, 10),
    ("", "buy", 1, 10),
    ("AAPL", "buy", "abc", 10),
])
def test_invalid_inputs(ticker, side, qty, price):
    with pytest.raises(ValueError):
        db.execute_trade_tx(ticker, side, qty, price)
    assert db.list_trades() == []
    assert db.get_cash() == 10000.0


def test_atomic_rollback_on_midway_failure(monkeypatch):
    from app.db import repository as repo

    def boom(*a, **k):
        raise RuntimeError("fail")

    monkeypatch.setattr(repo, "_insert_trade", boom)
    with pytest.raises(RuntimeError):
        db.execute_trade_tx("AAPL", "buy", 1, 100.0)
    assert db.get_cash() == 10000.0
    assert db.list_positions() == []


def test_concurrent_buys_never_overspend():
    db.init_db()
    results = []

    def worker():
        try:
            db.execute_trade_tx("AAPL", "buy", 1, 100.0)
            results.append(True)
        except ValueError:
            results.append(False)

    threads = [threading.Thread(target=worker) for _ in range(150)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(results) == 100
    assert db.get_cash() == pytest.approx(0.0)
    assert db.get_position("AAPL")["quantity"] == 100
