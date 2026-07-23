import asyncio

from fastapi import APIRouter

from backend.agent import run_agent_response
from backend.app.demo import demo_reply
from backend.app.errors import UpstreamServiceError
from backend.app.schemas import ChatRequest
from backend.config import get_settings


router = APIRouter(prefix="/api")


@router.post("/chat")
async def chat(request: ChatRequest) -> dict:
    mode = get_settings().chat_mode
    if mode == "unconfigured":
        return {
            "reply": "Conversational chat is not configured yet. Add OPENAI_API_KEY to backend/.env and restart the services.",
            "citations": [],
            "mode": mode,
        }
    history = [item.model_dump() for item in request.history]
    try:
        if mode == "demo":
            return {"reply": await demo_reply(request.message, history), "citations": [], "mode": mode}
        response = await asyncio.to_thread(run_agent_response, request.message, history)
        return {**response, "mode": mode}
    except Exception as error:
        raise UpstreamServiceError("The insurance adviser or MCP proxy is unavailable.") from error
