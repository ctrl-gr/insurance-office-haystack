from __future__ import annotations

import asyncio
import uuid
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query, Response, status

from backend.agent import run_agent_response
from backend.app.demo import demo_reply
from backend.app.errors import UpstreamServiceError
from backend.app.schemas import ChatRequest, SessionMessageRequest
from backend.config import get_settings
from backend.conversations import (
    ConversationNotFoundError,
    MongoConversationRepository,
)


router = APIRouter(prefix="/api")


@lru_cache(maxsize=1)
def get_conversation_repository() -> MongoConversationRepository:
    return MongoConversationRepository(get_settings())


def _history(messages: list[dict]) -> list[dict[str, str]]:
    return [
        {"role": message["role"], "content": message["content"]}
        for message in messages[-40:]
    ]


async def _generate_reply(
    message: str,
    history: list[dict[str, str]],
    session_id: str,
) -> dict:
    mode = get_settings().chat_mode
    if mode == "unconfigured":
        return {
            "reply": (
                "Conversational chat is not configured yet. "
                "Add OPENAI_API_KEY to backend/.env and restart the services."
            ),
            "citations": [],
            "mode": mode,
        }
    try:
        if mode == "demo":
            reply = await demo_reply(message, history, session_id)
            return {"reply": reply, "citations": [], "mode": mode}
        response = await asyncio.to_thread(
            run_agent_response,
            message,
            history,
            session_id,
        )
        return {**response, "mode": mode}
    except Exception as error:
        raise UpstreamServiceError(
            "The insurance adviser or MCP proxy is unavailable."
        ) from error


async def _persisted_reply(session_id: str, message: str) -> dict:
    repository = get_conversation_repository()
    try:
        existing = await asyncio.to_thread(
            repository.list_messages,
            session_id,
            40,
        )
        await asyncio.to_thread(
            repository.append_message,
            session_id,
            "user",
            message,
        )
        response = await _generate_reply(message, _history(existing), session_id)
        saved = await asyncio.to_thread(
            repository.append_message,
            session_id,
            "assistant",
            response["reply"],
            response["citations"],
        )
        return {**response, "sessionId": session_id, "message": saved}
    except ConversationNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session() -> dict:
    session = await asyncio.to_thread(
        get_conversation_repository().create_session
    )
    return {**session, "messages": []}


@router.get("/sessions")
async def list_sessions(
    limit: int = Query(default=50, ge=1, le=100),
) -> dict:
    sessions = await asyncio.to_thread(
        get_conversation_repository().list_sessions,
        limit,
    )
    return {"sessions": sessions}


@router.get("/sessions/{session_id}/messages")
async def session_messages(session_id: str) -> dict:
    try:
        messages = await asyncio.to_thread(
            get_conversation_repository().list_messages,
            session_id,
            100,
        )
        return {"sessionId": session_id, "messages": messages}
    except ConversationNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/sessions/{session_id}/messages")
async def send_session_message(
    session_id: str,
    request: SessionMessageRequest,
) -> dict:
    return await _persisted_reply(session_id, request.message)


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_session(session_id: str) -> Response:
    try:
        await asyncio.to_thread(
            get_conversation_repository().delete_session,
            session_id,
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ConversationNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/chat")
async def chat(request: ChatRequest) -> dict:
    if request.sessionId:
        return await _persisted_reply(request.sessionId, request.message)
    legacy_session_id = f"S-{uuid.uuid4().hex.upper()}"
    history = [item.model_dump() for item in request.history]
    response = await _generate_reply(
        request.message,
        history,
        legacy_session_id,
    )
    return {**response, "sessionId": legacy_session_id}
