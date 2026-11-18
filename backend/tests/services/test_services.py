import pytest

from app.services import portfolio as pf


def _state(client):
    return client.app.state.app_state


def test_trade_validation_and_pnl(client):
    st = _state(client)
    st.cache.update("AAPL", 100.0)
    pf.execute_trade(st.cache, "AAPL", "buy", 10)
    st.cache.update("AAPL", 110.0)
    p = pf.build_portfolio(st.cache)
    assert p["unrealized_pnl"] == pytest.approx(100.0)
    assert p["total_value"] == pytest.approx(10100.0)
    assert p["positions"][0]["pnl_pct"] == pytest.approx(10.0)
    with pytest.raises(pf.TradeError):
        pf.execute_trade(st.cache, "AAPL", "sell", 11)
    with pytest.raises(pf.TradeError):
        pf.execute_trade(st.cache, "AAPL", "buy", float("nan"))


def test_missing_price_values_at_cost(client):
    st = _state(client)
    st.cache.update("AAPL", 100.0)
    pf.execute_trade(st.cache, "AAPL", "buy", 1)
    st.cache.remove("AAPL")
    assert pf.build_portfolio(st.cache)["total_value"] == pytest.approx(10000.0)


async def test_chat_reports_failed_trade(client, monkeypatch):
    from app import llm
    from app.services import chat

    async def fake(message, portfolio, history):
        return llm.ChatLLMResponse(
            message="Buying",
            trades=[{"ticker": "AAPL", "side": "buy", "quantity": 1e9}],
            watchlist_changes=[{"ticker": "!!", "action": "add"}],
        )

    monkeypatch.setattr(llm, "get_chat_response", fake)
    out = await chat.handle_chat(_state(client), "go")
    assert out["trades"][0]["status"] == "failed" and out["trades"][0]["error"]
    assert out["watchlist_changes"][0]["status"] == "failed"
    assert "Could not complete" in out["message"]
