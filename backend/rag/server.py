from __future__ import annotations

import logging
import time
import uuid
from typing import Literal

from mcp.server.fastmcp import FastMCP

from backend.config import get_settings
from backend.mcp_audit import audit, get_audit_logger
from .service import InsuranceConditionsRag


PolicyCategory = Literal["Car", "Injuries", "Home"]
settings = get_settings()
rag = InsuranceConditionsRag(settings)
logger = get_audit_logger("conditions")

mcp = FastMCP(
    "Insurance Conditions RAG",
    instructions="Retrieve grounded insurance policy conditions from the insurance_conditions database.",
    host="127.0.0.1",
    port=5084,
    stateless_http=True,
    json_response=True,
)


@mcp.tool(name="search_conditions")
def search_conditions(
    query: str,
    category: PolicyCategory | None = None,
    policy_name: str | None = None,
    top_k: int = 5,
    request_id: str | None = None,
) -> dict:
    """Retrieve relevant policy wording from insurance_conditions. Use filters when the provider or product is known."""
    trace_id = request_id or str(uuid.uuid4())
    started = time.perf_counter()
    audit(
        logger,
        "conditions",
        "rag.started",
        request_id=trace_id,
        tool="search_conditions",
        category=category,
        policy_name=policy_name,
        top_k=top_k,
    )
    try:
        if not query.strip():
            raise ValueError("query must not be empty")
        if not 1 <= top_k <= 10:
            raise ValueError("top_k must be between 1 and 10")
        matches = rag.search(query, category, policy_name, top_k)
        audit(
            logger,
            "conditions",
            "rag.completed",
            request_id=trace_id,
            tool="search_conditions",
            status="success",
            result_count=len(matches),
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return {"matches": matches, "resultCount": len(matches)}
    except Exception as error:
        audit(
            logger,
            "conditions",
            "rag.failed",
            level=logging.ERROR,
            request_id=trace_id,
            tool="search_conditions",
            status="error",
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            error_type=type(error).__name__,
            error=str(error),
        )
        raise


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
