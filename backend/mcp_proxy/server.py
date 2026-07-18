from __future__ import annotations

import logging
import time
import uuid

from mcp.server.fastmcp import FastMCP

from backend.config import get_settings
from backend.mcp_audit import audit, get_audit_logger
from backend.mcp_servers.company import CoverageType
from .client import call_mcp_tool


COMPANY_URLS = get_settings().company_urls
AUDIT_LOGGER = get_audit_logger("proxy")

proxy = FastMCP(
    "Insurance MCP Proxy",
    instructions="Namespaced gateway for the three independent insurance company MCP servers.",
    host="127.0.0.1",
    port=5275,
    stateless_http=True,
    json_response=True,
)


async def _route(company_id: str, tool_name: str, arguments: dict) -> dict:
    request_id = str(uuid.uuid4())
    namespaced_tool = f"{company_id}_{tool_name}"
    started = time.perf_counter()
    audit(
        AUDIT_LOGGER,
        "proxy",
        "route.started",
        request_id=request_id,
        company=company_id,
        tool=namespaced_tool,
        argument_names=sorted(arguments),
    )
    try:
        result = await call_mcp_tool(
            COMPANY_URLS[company_id],
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
            company=company_id,
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
            company=company_id,
            tool=namespaced_tool,
            status="error",
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            error_type=type(error).__name__,
            error=str(error),
        )
        raise


@proxy.tool()
def list_company_tools() -> dict:
    """List every namespaced tool exposed by the connected insurance companies."""
    return {
        "tools": [
            f"{company}_{tool}"
            for company in COMPANY_URLS
            for tool in ("get_quote", "check_coverage", "purchase_policy")
        ]
    }


@proxy.tool(name="thelion_get_quote")
async def lion_get_quote(client_age: int, coverage_type: CoverageType, asset_value: float) -> dict:
    """Get a Lion quote. coverage_type must be auto, home, or life; car coverages use auto."""
    return await _route("thelion", "get_quote", {"client_age": client_age, "coverage_type": coverage_type, "asset_value": asset_value})


@proxy.tool(name="thebluecompany_get_quote")
async def blue_get_quote(client_age: int, coverage_type: CoverageType, asset_value: float) -> dict:
    """Get a Blue quote. coverage_type must be auto, home, or life; car coverages use auto."""
    return await _route("thebluecompany", "get_quote", {"client_age": client_age, "coverage_type": coverage_type, "asset_value": asset_value})


@proxy.tool(name="thethreelines_get_quote")
async def three_lines_get_quote(client_age: int, coverage_type: CoverageType, asset_value: float) -> dict:
    """Get a Three Lines quote. coverage_type must be auto, home, or life; car coverages use auto."""
    return await _route("thethreelines", "get_quote", {"client_age": client_age, "coverage_type": coverage_type, "asset_value": asset_value})


@proxy.tool(name="thelion_check_coverage")
async def lion_check_coverage(coverage_type: CoverageType) -> dict:
    """Check Lion coverage. Use auto for any car guarantee such as collision or theft."""
    return await _route("thelion", "check_coverage", {"coverage_type": coverage_type})


@proxy.tool(name="thebluecompany_check_coverage")
async def blue_check_coverage(coverage_type: CoverageType) -> dict:
    """Check Blue coverage. Use auto for any car guarantee such as collision or theft."""
    return await _route("thebluecompany", "check_coverage", {"coverage_type": coverage_type})


@proxy.tool(name="thethreelines_check_coverage")
async def three_lines_check_coverage(coverage_type: CoverageType) -> dict:
    """Check Three Lines coverage. Use auto for any car guarantee such as collision or theft."""
    return await _route("thethreelines", "check_coverage", {"coverage_type": coverage_type})


@proxy.tool(name="thelion_purchase_policy")
async def lion_purchase_policy(annual_premium: float, quote_id: str | None = None) -> dict:
    """Purchase a previously issued Lion quote. Pass quote_id when available."""
    arguments = {"annual_premium": annual_premium, **({"quote_id": quote_id} if quote_id else {})}
    return await _route("thelion", "purchase_policy", arguments)


@proxy.tool(name="thebluecompany_purchase_policy")
async def blue_purchase_policy(annual_premium: float, quote_id: str | None = None) -> dict:
    """Purchase a previously issued Blue quote. Pass quote_id when available."""
    arguments = {"annual_premium": annual_premium, **({"quote_id": quote_id} if quote_id else {})}
    return await _route("thebluecompany", "purchase_policy", arguments)


@proxy.tool(name="thethreelines_purchase_policy")
async def three_lines_purchase_policy(annual_premium: float, quote_id: str | None = None) -> dict:
    """Purchase a previously issued Three Lines quote. Pass quote_id when available."""
    arguments = {"annual_premium": annual_premium, **({"quote_id": quote_id} if quote_id else {})}
    return await _route("thethreelines", "purchase_policy", arguments)


if __name__ == "__main__":
    proxy.run(transport="streamable-http")
