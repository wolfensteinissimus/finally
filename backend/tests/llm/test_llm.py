"""LLM tests; litellm is always mocked."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.llm import client
from app.llm.prompts import build_messages
from app.llm.schema import ChatLLMResponse

PORTFOLIO = {
    "cash": 5000.0,
    "total_value": 10000.0,
    "unrealized_pnl": 12.5,
    "positions": [
        {"ticker": "AAPL", "quantity": 5, "avg_cost": 190, "current_price": 192,
         "unrealized_pnl": 10, "pnl_pct": 1.0}
    ],
    "watchlist": [{"ticker": "MSFT", "price": 400}],
}


def _resp(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


@pytest.fixture
def no_mock(monkeypatch):
    monkeypatch.delenv("LLM_MOCK", raising=False)


async def test_mock_buy(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    r = await client.get_chat_response("Please buy something", {}, [])
    assert r.trades[0].ticker == "AAPL" and r.trades[0].side == "buy" and r.trades[0].quantity == 1


async def test_mock_add_remove_and_generic(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    r = await client.get_chat_response("add pypl", {}, [])
    assert r.watchlist_changes[0].ticker == "PYPL" and r.watchlist_changes[0].action == "add"
    r = await client.get_chat_response("remove NFLX", {}, [])
    assert r.watchlist_changes[0].action == "remove"
    r = await client.get_chat_response("how am I doing?", {}, [])
    assert r.message and not r.trades and not r.watchlist_changes


async def test_mock_never_calls_litellm(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    m = AsyncMock()
    monkeypatch.setattr(client, "acompletion", m)
    await client.get_chat_response("hi", {}, [])
    m.assert_not_called()


async def test_real_path_parses_structured(no_mock, monkeypatch):
    m = AsyncMock(return_value=_resp(
        '{"message":"Done","trades":[{"ticker":"aapl","side":"BUY","quantity":3}],'
        '"watchlist_changes":[{"ticker":"pypl","action":"add"}]}'
    ))
    monkeypatch.setattr(client, "acompletion", m)
    r = await client.get_chat_response("buy 3 aapl", PORTFOLIO, [])
    assert r.trades[0].ticker == "AAPL" and r.trades[0].side == "buy"
    assert r.watchlist_changes[0].ticker == "PYPL"
    kw = m.call_args.kwargs
    assert kw["model"] == client.MODEL
    assert kw["response_format"] is ChatLLMResponse
    assert kw["extra_body"] == {"provider": {"order": ["cerebras"]}}


async def test_optional_fields_default(no_mock, monkeypatch):
    monkeypatch.setattr(client, "acompletion", AsyncMock(return_value=_resp('{"message":"hi"}')))
    r = await client.get_chat_response("x", PORTFOLIO, [])
    assert r.trades == [] and r.watchlist_changes == []


@pytest.mark.parametrize("bad", [
    "not json", "", None, '{"trades": []}',
    '{"message":"x","trades":[{"ticker":"A","side":"hold","quantity":1}]}',
    '{"message":"x","trades":[{"ticker":"A","side":"buy","quantity":-1}]}',
])
async def test_malformed_falls_back(no_mock, monkeypatch, bad):
    monkeypatch.setattr(client, "acompletion", AsyncMock(return_value=_resp(bad)))
    r = await client.get_chat_response("x", PORTFOLIO, [])
    assert r.message == client.FALLBACK_MESSAGE and r.trades == []


async def test_fenced_and_embedded_json(no_mock, monkeypatch):
    monkeypatch.setattr(client, "acompletion",
                        AsyncMock(return_value=_resp('```json\n{"message":"ok"}\n```')))
    assert (await client.get_chat_response("x", {}, [])).message == "ok"
    monkeypatch.setattr(client, "acompletion",
                        AsyncMock(return_value=_resp('Sure! {"message":"ok2"} bye')))
    assert (await client.get_chat_response("x", {}, [])).message == "ok2"


async def test_exception_falls_back(no_mock, monkeypatch):
    monkeypatch.setattr(client, "acompletion", AsyncMock(side_effect=RuntimeError("boom")))
    r = await client.get_chat_response("x", {}, [])
    assert r.message == client.FALLBACK_MESSAGE


def test_build_messages_includes_context_and_history():
    history = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"},
               {"role": "system", "content": "ignored"}]
    msgs = build_messages("buy msft", PORTFOLIO, history)
    assert msgs[0]["role"] == "system" and "FinAlly" in msgs[0]["content"]
    assert "AAPL" in msgs[1]["content"] and "MSFT" in msgs[1]["content"]
    assert "$5,000.00" in msgs[1]["content"]
    assert [m["content"] for m in msgs[2:]] == ["hello", "hi", "buy msft"]
