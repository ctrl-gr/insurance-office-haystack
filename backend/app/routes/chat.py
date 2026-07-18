import asyncio

from fastapi import APIRouter

from backend.agent import run_agent
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
            "mode": mode,
        }
    history = [item.model_dump() for item in request.history]
    try:
        if mode == "demo":
            return {"reply": await demo_reply(request.message, history), "mode": mode}
        reply = await asyncio.to_thread(run_agent, request.message, history)
        return {"reply": reply, "mode": mode}
    except Exception as error:
        raise UpstreamServiceError("The insurance adviser or MCP proxy is unavailable.") from error
