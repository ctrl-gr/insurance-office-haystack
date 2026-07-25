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


def _choice(name: str, default: str, allowed: set[str]) -> str:
    value = os.getenv(name, default).strip().lower()
    if value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise ValueError(f"{name} must be one of: {choices}")
    return value


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
    conditions_mcp_url: str
    mongodb_uri: str
    mongodb_database: str
    mongodb_policies_collection: str
    mongodb_chunks_collection: str
    mongodb_vector_index: str
    mongodb_server_selection_timeout_ms: int
    conditions_auto_ingest: bool
    rag_retrieval_mode: str
    rag_embedding_model: str
    rag_embedding_dimensions: int
    rag_vector_candidates: int
    rag_hybrid_rrf_k: int
    rag_chunk_size_words: int
    rag_chunk_overlap_words: int
    pdf_download_timeout_seconds: float
    pdf_max_bytes: int
    pdf_storage_bearer_token: str | None
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
    def mcp_service_urls(self) -> dict[str, str]:
        return {**self.company_urls, "conditions": self.conditions_mcp_url}

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
        conditions_mcp_url=os.getenv("CONDITIONS_MCP_URL", "http://127.0.0.1:5084/mcp"),
        mongodb_uri=os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017"),
        mongodb_database=os.getenv("MONGODB_DATABASE", "insurance_office"),
        mongodb_policies_collection=os.getenv("MONGODB_POLICIES_COLLECTION", "policy_conditions"),
        mongodb_chunks_collection=os.getenv("MONGODB_CHUNKS_COLLECTION", "insurance_condition_chunks"),
        mongodb_vector_index=os.getenv(
            "MONGODB_VECTOR_INDEX",
            "condition_chunk_vector_index",
        ).strip(),
        mongodb_server_selection_timeout_ms=int(os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "5000")),
        conditions_auto_ingest=_boolean("CONDITIONS_AUTO_INGEST"),
        rag_retrieval_mode=_choice("RAG_RETRIEVAL_MODE", "text", {"text", "hybrid"}),
        rag_embedding_model=os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-3-small").strip(),
        rag_embedding_dimensions=int(os.getenv("RAG_EMBEDDING_DIMENSIONS", "1536")),
        rag_vector_candidates=int(os.getenv("RAG_VECTOR_CANDIDATES", "50")),
        rag_hybrid_rrf_k=int(os.getenv("RAG_HYBRID_RRF_K", "60")),
        rag_chunk_size_words=int(os.getenv("RAG_CHUNK_SIZE_WORDS", "500")),
        rag_chunk_overlap_words=int(os.getenv("RAG_CHUNK_OVERLAP_WORDS", "75")),
        pdf_download_timeout_seconds=float(os.getenv("PDF_DOWNLOAD_TIMEOUT_SECONDS", "30")),
        pdf_max_bytes=int(os.getenv("PDF_MAX_BYTES", "25000000")),
        pdf_storage_bearer_token=os.getenv("PDF_STORAGE_BEARER_TOKEN", "").strip() or None,
        mcp_log_dir=log_dir,
        mcp_log_max_bytes=int(os.getenv("MCP_LOG_MAX_BYTES", "5000000")),
        mcp_log_backup_count=int(os.getenv("MCP_LOG_BACKUP_COUNT", "5")),
        quote_ttl_seconds=int(os.getenv("QUOTE_TTL_SECONDS", "1800")),
    )


load_environment()
