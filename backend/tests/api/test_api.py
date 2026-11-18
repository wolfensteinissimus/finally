def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_initial_portfolio(client):
    p = client.get("/api/portfolio").json()
    assert p["cash"] == 10000.0
    assert p["total_value"] == 10000.0
    assert p["positions"] == []


def test_buy_and_sell(client):
    r = client.post("/api/portfolio/trade", json={"ticker": "aapl", "quantity": 2, "side": "buy"})
    assert r.status_code == 200
    p = r.json()
    assert p["cash"] < 10000.0
    pos = p["positions"][0]
    assert pos["ticker"] == "AAPL" and pos["quantity"] == 2
    assert set(pos) >= {"avg_cost", "current_price", "market_value", "unrealized_pnl", "pnl_pct"}
    r = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 2, "side": "sell"})
    assert r.status_code == 200 and r.json()["positions"] == []


def test_trade_errors(client):
    bad = [
        {"ticker": "AAPL", "quantity": 1_000_000, "side": "buy"},
        {"ticker": "AAPL", "quantity": 1, "side": "sell"},
        {"ticker": "AAPL", "quantity": 0, "side": "buy"},
        {"ticker": "AAPL", "quantity": -1, "side": "buy"},
        {"ticker": "AAPL", "quantity": 1, "side": "hold"},
        {"ticker": "ZZZZ", "quantity": 1, "side": "buy"},
    ]
    for body in bad:
        r = client.post("/api/portfolio/trade", json=body)
        assert r.status_code == 400, body
        assert r.json()["detail"]


def test_history_has_snapshot_after_trade(client):
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
    h = client.get("/api/portfolio/history").json()
    assert len(h) >= 1 and set(h[0]) == {"recorded_at", "total_value"}


def test_watchlist_crud(client):
    wl = client.get("/api/watchlist").json()
    assert len(wl) == 10 and {"ticker", "price", "previous_price", "change_pct"} <= set(wl[0])
    r = client.post("/api/watchlist", json={"ticker": "pypl"})
    assert r.status_code == 200
    assert "PYPL" in [w["ticker"] for w in r.json()]
    assert client.post("/api/watchlist", json={"ticker": "bad ticker!"}).status_code == 400
    r = client.delete("/api/watchlist/PYPL")
    assert "PYPL" not in [w["ticker"] for w in r.json()]


def test_remove_held_ticker_keeps_price(client):
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
    client.delete("/api/watchlist/AAPL")
    p = client.get("/api/portfolio").json()
    assert p["positions"][0]["current_price"] > 0


def test_chat_mock_buy_and_add(client):
    r = client.post("/api/chat", json={"message": "please buy some"})
    assert r.status_code == 200
    body = r.json()
    assert body["message"]
    assert body["trades"] and body["trades"][0]["status"] == "executed"
    assert client.get("/api/portfolio").json()["positions"]
    r = client.post("/api/chat", json={"message": "add PYPL"}).json()
    assert r["watchlist_changes"][0]["status"] == "executed"


def test_chat_empty(client):
    assert client.post("/api/chat", json={"message": "  "}).status_code == 400


def test_static_and_spa_fallback(client):
    assert "INDEX" in client.get("/").text
    assert "console.log" in client.get("/app.js").text
    assert "INDEX" in client.get("/some/route").text
    assert client.get("/api/nope").status_code == 404
