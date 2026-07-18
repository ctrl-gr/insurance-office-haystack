from fastapi import APIRouter

from backend.application.insurance import PROVIDERS
from backend.config import get_settings
from backend.mcp_proxy.client import call_proxy_tool


router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    try:
        discovered = await call_proxy_tool("list_company_tools", {})
        return {"status": "ok", "engine": "Haystack", "proxy": "connected", "toolCount": len(discovered["tools"]), "mode": settings.chat_mode}
    except Exception:
        return {"status": "degraded", "engine": "Haystack", "proxy": "unavailable", "toolCount": 0, "mode": settings.chat_mode}


@router.get("/providers")
def providers() -> dict:
    return {"providers": PROVIDERS}
