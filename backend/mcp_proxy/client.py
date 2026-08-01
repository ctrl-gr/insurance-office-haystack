from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp import Client
from mcp.types import TextContent, Tool

from backend.config import get_settings
from backend.mcp_protocol import MCP_PROTOCOL_VERSION


async def _with_timeout(operation, timeout: float):
    return await asyncio.wait_for(operation, timeout=timeout)


async def discover_mcp_tools(url: str, timeout: float = 10) -> list[Tool]:
    """Discover tools through the MCP 2026-07-28 server/discover flow."""

    async def discover() -> list[Tool]:
        async with Client(url, mode="auto") as client:
            if client.protocol_version != MCP_PROTOCOL_VERSION:
                raise RuntimeError(
                    f"MCP server at {url} negotiated {client.protocol_version}; "
                    f"expected {MCP_PROTOCOL_VERSION}"
                )
            tools: list[Tool] = []
            cursor: str | None = None
            while True:
                page = await client.list_tools(cursor=cursor)
                tools.extend(page.tools)
                if page.next_cursor is None:
                    return tools
                cursor = page.next_cursor

    return await _with_timeout(discover(), timeout)


def _text_result(result: Any) -> str | None:
    for block in result.content:
        if isinstance(block, TextContent):
            return block.text
    return None


async def call_mcp_tool(
    url: str,
    tool_name: str,
    arguments: dict[str, Any],
    timeout: float = 30,
) -> Any:
    """Call an internal server using the sessionless MCP 2026-07-28 protocol."""

    async def invoke() -> Any:
        async with Client(url, mode=MCP_PROTOCOL_VERSION) as client:
            return await client.call_tool(tool_name, arguments)

    result = await _with_timeout(invoke(), timeout)
    if result.is_error:
        raise RuntimeError(_text_result(result) or f"MCP tool {tool_name} failed")

    structured = result.structured_content
    if structured is not None:
        if isinstance(structured, dict) and set(structured) == {"result"}:
            return structured["result"]
        return structured

    text = _text_result(result)
    if text is not None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    raise RuntimeError(f"MCP tool {tool_name} returned no usable content")


async def call_proxy_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    return await call_mcp_tool(get_settings().mcp_proxy_url, tool_name, arguments)
