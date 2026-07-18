from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values


BACKEND_DIR = Path(__file__).resolve().parent
ENV_FILE = BACKEND_DIR / ".env"


def load_environment() -> None:
    """Load non-empty local values only when the process has no value of its own."""
    if not ENV_FILE.exists():
        return
    for name, value in dotenv_values(ENV_FILE).items():
        if value and not os.getenv(name, "").strip():
            os.environ[name] = value


def _boolean(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    openai_reasoning_effort: str | None
    demo_mode: bool
    cors_origins: tuple[str, ...]
    mcp_proxy_url: str
    lion_mcp_url: str
    blue_mcp_url: str
    three_lines_mcp_url: str
    mcp_log_dir: Path
    mcp_log_max_bytes: int
    mcp_log_backup_count: int
    quote_ttl_seconds: int

    @property
    def chat_mode(self) -> str:
        if self.openai_api_key:
            return "live"
        return "demo" if self.demo_mode else "unconfigured"

    @property
    def company_urls(self) -> dict[str, str]:
        return {
            "thelion": self.lion_mcp_url,
            "thebluecompany": self.blue_mcp_url,
            "thethreelines": self.three_lines_mcp_url,
        }

    @property
    def generation_kwargs(self) -> dict[str, str]:
        if self.openai_reasoning_effort:
            return {"reasoning_effort": self.openai_reasoning_effort}
        if self.openai_model.startswith("gpt-5.6"):
            return {"reasoning_effort": "none"}
        return {}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_environment()
    origins = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    )
    log_dir = Path(os.getenv("MCP_LOG_DIR", str(BACKEND_DIR / "logs")))
    if not log_dir.is_absolute():
        log_dir = BACKEND_DIR.parent / log_dir
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip(),
        openai_reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", "").strip() or None,
        demo_mode=_boolean("DEMO_MODE"),
        cors_origins=origins,
        mcp_proxy_url=os.getenv("MCP_PROXY_URL", "http://127.0.0.1:5275/mcp"),
        lion_mcp_url=os.getenv("LION_MCP_URL", "http://127.0.0.1:5081/mcp"),
        blue_mcp_url=os.getenv("BLUE_MCP_URL", "http://127.0.0.1:5082/mcp"),
        three_lines_mcp_url=os.getenv("THREE_LINES_MCP_URL", "http://127.0.0.1:5083/mcp"),
        mcp_log_dir=log_dir,
        mcp_log_max_bytes=int(os.getenv("MCP_LOG_MAX_BYTES", "5000000")),
        mcp_log_backup_count=int(os.getenv("MCP_LOG_BACKUP_COUNT", "5")),
        quote_ttl_seconds=int(os.getenv("QUOTE_TTL_SECONDS", "1800")),
    )


load_environment()
