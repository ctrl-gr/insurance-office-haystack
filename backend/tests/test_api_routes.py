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
            json={
                "age": 35,
                "coverageType": "auto",
                "assetValue": 25_000,
                "sessionId": "S-" + "A" * 32,
            },
        )
    )

    assert response.status_code == 200
    assert response.json()["bestValueProviderId"] == "blue"
    compare.assert_awaited_once_with(35, "auto", 25_000, "S-" + "A" * 32)


def test_unconfigured_chat_returns_actionable_reply_without_upstream_call(monkeypatch):
    monkeypatch.setattr(chat_routes, "get_settings", lambda: type("Settings", (), {"chat_mode": "unconfigured"})())

    response = asyncio.run(request("POST", "/api/chat", json={"message": "Hello", "history": []}))

    assert response.status_code == 200
    assert response.json()["mode"] == "unconfigured"
    assert response.json()["citations"] == []
    assert "OPENAI_API_KEY" in response.json()["reply"]


def test_unknown_provider_is_rejected_before_mcp_call():
    response = asyncio.run(request("GET", "/api/coverage/auto?provider_id=unknown"))

    assert response.status_code == 404


class FakeConversationRepository:
    def __init__(self):
        self.messages = []

    def create_session(self):
        return {
            "sessionId": "S-" + "B" * 32,
            "status": "active",
            "createdAt": "2026-01-01T00:00:00+00:00",
            "updatedAt": "2026-01-01T00:00:00+00:00",
        }

    def list_messages(self, session_id, limit=100):
        return self.messages[-limit:]

    def append_message(self, session_id, role, content, citations=None):
        message = {
            "id": str(len(self.messages) + 1),
            "sessionId": session_id,
            "sequence": len(self.messages) + 1,
            "role": role,
            "content": content,
            "citations": citations or [],
            "createdAt": "2026-01-01T00:00:00+00:00",
        }
        self.messages.append(message)
        return message


def test_session_message_is_stored_server_side(monkeypatch):
    repository = FakeConversationRepository()
    monkeypatch.setattr(
        chat_routes,
        "get_conversation_repository",
        lambda: repository,
    )
    monkeypatch.setattr(
        chat_routes,
        "get_settings",
        lambda: type("Settings", (), {"chat_mode": "unconfigured"})(),
    )
    session_id = "S-" + "B" * 32

    response = asyncio.run(
        request(
            "POST",
            f"/api/sessions/{session_id}/messages",
            json={"message": "Hello"},
        )
    )

    assert response.status_code == 200
    assert [message["role"] for message in repository.messages] == [
        "user",
        "assistant",
    ]
    assert response.json()["sessionId"] == session_id


def test_existing_session_messages_can_be_resumed(monkeypatch):
    repository = FakeConversationRepository()
    repository.append_message(
        "S-" + "B" * 32,
        "assistant",
        "Welcome back",
    )
    monkeypatch.setattr(
        chat_routes,
        "get_conversation_repository",
        lambda: repository,
    )

    response = asyncio.run(
        request(
            "GET",
            f"/api/sessions/{'S-' + 'B' * 32}/messages",
        )
    )

    assert response.status_code == 200
    assert response.json()["messages"][0]["content"] == "Welcome back"
