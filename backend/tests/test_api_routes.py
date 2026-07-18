import asyncio
from unittest.mock import AsyncMock

import httpx

import backend.app.routes.chat as chat_routes
import backend.app.routes.insurance as insurance_routes
from backend.app.main import app


async def request(method: str, url: str, **kwargs) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, url, **kwargs)


def test_quotes_route_preserves_frontend_contract(monkeypatch):
    compare = AsyncMock(
        return_value={
            "quotes": [{"providerId": "blue", "annualPremium": 1000.0, "rank": 1}],
            "bestValueProviderId": "blue",
        }
    )
    monkeypatch.setattr(insurance_routes, "compare_quotes", compare)

    response = asyncio.run(
        request(
            "POST",
            "/api/quotes",
            json={"age": 35, "coverageType": "auto", "assetValue": 25_000},
        )
    )

    assert response.status_code == 200
    assert response.json()["bestValueProviderId"] == "blue"
    compare.assert_awaited_once_with(35, "auto", 25_000)


def test_unconfigured_chat_returns_actionable_reply_without_upstream_call(monkeypatch):
    monkeypatch.setattr(chat_routes, "get_settings", lambda: type("Settings", (), {"chat_mode": "unconfigured"})())

    response = asyncio.run(request("POST", "/api/chat", json={"message": "Hello", "history": []}))

    assert response.status_code == 200
    assert response.json()["mode"] == "unconfigured"
    assert "OPENAI_API_KEY" in response.json()["reply"]


def test_unknown_provider_is_rejected_before_mcp_call():
    response = asyncio.run(request("GET", "/api/coverage/auto?provider_id=unknown"))

    assert response.status_code == 404
