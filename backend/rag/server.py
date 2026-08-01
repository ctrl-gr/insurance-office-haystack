from __future__ import annotations

import logging
import time
import uuid

from mcp.server import MCPServer

from backend.config import get_settings
from backend.mcp_audit import audit, get_audit_logger
from backend.mcp_protocol import MCP_SERVER_VERSION, streamable_http_options

from .coverage_mapping import CoverageType, category_for_coverage
from .service import InsuranceConditionsRag


settings = get_settings()
rag = InsuranceConditionsRag(settings)
logger = get_audit_logger("conditions")

mcp = MCPServer(
    "Insurance Conditions RAG",
    instructions="Retrieve shared grounded policy conditions from the policy_conditions database by coverage type.",
    version=MCP_SERVER_VERSION,
)


@mcp.tool(name="search_conditions")
def search_conditions(
    query: str,
    coverage_type: CoverageType,
    top_k: int = 5,
    request_id: str | None = None,
) -> dict:
    """Retrieve shared policy wording for auto, home, or life. Conditions are identical for all three companies."""
    trace_id = request_id or str(uuid.uuid4())
    started = time.perf_counter()
    category = category_for_coverage(coverage_type)
    audit(
        logger,
        "conditions",
        "rag.started",
        request_id=trace_id,
        tool="search_conditions",
        category=category,
        coverage_type=coverage_type,
        top_k=top_k,
    )
    try:
        if not query.strip():
            raise ValueError("query must not be empty")
        if not 1 <= top_k <= 10:
            raise ValueError("top_k must be between 1 and 10")
        matches = rag.search(query, category=category, top_k=top_k)
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
    mcp.run(**streamable_http_options(5084))
