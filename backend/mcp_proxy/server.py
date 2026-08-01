from __future__ import annotations

import logging
import time
import uuid

from mcp.server import MCPServer

from backend.config import get_settings
from backend.mcp_audit import audit, get_audit_logger
from backend.mcp_protocol import MCP_SERVER_VERSION, streamable_http_options
from backend.mcp_servers.company import CoverageType
from .client import call_mcp_tool


SETTINGS = get_settings()
SERVICE_URLS = SETTINGS.mcp_service_urls
COMPANY_IDS = tuple(SETTINGS.company_urls)
COMPANY_NAMES = {
    "thelion": "Lion",
    "thebluecompany": "Blue",
    "thethreelines": "Three Lines",
}
COMPANY_OPERATIONS = ("get_quote", "check_coverage", "purchase_policy")
COMPANY_TOOL_NAMES = tuple(
    f"{company_id}_{operation}"
    for company_id in COMPANY_IDS
    for operation in COMPANY_OPERATIONS
)
AUDIT_LOGGER = get_audit_logger("proxy")

proxy = MCPServer(
    "Insurance MCP Proxy",
    instructions="Gateway for three insurance company MCP servers and the insurance conditions RAG service.",
    version=MCP_SERVER_VERSION,
)


async def _route(service_id: str, tool_name: str, arguments: dict, exposed_tool_name: str | None = None) -> dict:
    request_id = str(uuid.uuid4())
    namespaced_tool = exposed_tool_name or f"{service_id}_{tool_name}"
    started = time.perf_counter()
    audit(
        AUDIT_LOGGER,
        "proxy",
        "route.started",
        request_id=request_id,
        company=service_id,
        tool=namespaced_tool,
        argument_names=sorted(arguments),
    )
    try:
        result = await call_mcp_tool(
            SERVICE_URLS[service_id],
            tool_name,
            {**arguments, "request_id": request_id},
        )
        if not isinstance(result, dict):
            raise RuntimeError(f"{namespaced_tool} returned an invalid response")
        audit(
            AUDIT_LOGGER,
            "proxy",
            "route.completed",
            request_id=request_id,
            company=service_id,
            tool=namespaced_tool,
            status="success",
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return result
    except Exception as error:
        audit(
            AUDIT_LOGGER,
            "proxy",
            "route.failed",
            level=logging.ERROR,
            request_id=request_id,
            company=service_id,
            tool=namespaced_tool,
            status="error",
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            error_type=type(error).__name__,
            error=str(error),
        )
        raise


@proxy.tool()
def list_company_tools() -> dict:
    """List every insurance company tool and the insurance-conditions RAG tool."""
    return {"tools": [*COMPANY_TOOL_NAMES, "search_insurance_conditions"]}


@proxy.tool(name="search_insurance_conditions")
async def search_insurance_conditions(
    query: str,
    coverage_type: CoverageType,
    top_k: int = 5,
) -> dict:
    """Retrieve shared conditions for auto, home, or life. The detailed wording is the same for every company."""
    arguments = {
        "query": query,
        "coverage_type": coverage_type,
        "top_k": top_k,
    }
    return await _route("conditions", "search_conditions", arguments, "search_insurance_conditions")


def _register_company_tools(company_id: str) -> None:
    """Register one schema-stable set of proxy tools for a company."""
    company_name = COMPANY_NAMES[company_id]

    async def get_quote(
        client_age: int,
        coverage_type: CoverageType,
        asset_value: float,
        session_id: str,
    ) -> dict:
        arguments = {
            "client_age": client_age,
            "coverage_type": coverage_type,
            "asset_value": asset_value,
            "session_id": session_id,
        }
        return await _route(company_id, "get_quote", arguments)

    async def check_coverage(coverage_type: CoverageType) -> dict:
        return await _route(company_id, "check_coverage", {"coverage_type": coverage_type})

    async def purchase_policy(
        annual_premium: float,
        session_id: str,
        quote_id: str | None = None,
    ) -> dict:
        arguments = {"annual_premium": annual_premium, "session_id": session_id}
        if quote_id:
            arguments["quote_id"] = quote_id
        return await _route(company_id, "purchase_policy", arguments)

    proxy.tool(
        name=f"{company_id}_get_quote",
        description=(
            f"Get a {company_name} quote. coverage_type must be auto, home, or life; "
            "car coverages use auto."
        ),
    )(get_quote)
    proxy.tool(
        name=f"{company_id}_check_coverage",
        description=(
            f"Check {company_name} coverage. Use auto for any car guarantee such as "
            "collision or theft."
        ),
    )(check_coverage)
    proxy.tool(
        name=f"{company_id}_purchase_policy",
        description=(
            f"Purchase a previously issued {company_name} quote. Pass quote_id when "
            "available."
        ),
    )(purchase_policy)


for _company_id in COMPANY_IDS:
    _register_company_tools(_company_id)


if __name__ == "__main__":
    proxy.run(**streamable_http_options(5275))
