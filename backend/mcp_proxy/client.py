from __future__ import annotations

import json
from typing import Any

from mcp import ClientSession, types
from mcp.client.streamable_http import streamable_http_client

from backend.config import get_settings


async def call_mcp_tool(url: str, tool_name: str, arguments: dict[str, Any]) -> Any:
    async with streamable_http_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)

    structured = getattr(result, "structuredContent", None) or getattr(result, "structured_content", None)
    if structured is not None:
        return structured.get("result", structured) if isinstance(structured, dict) else structured

    for block in result.content:
        if isinstance(block, types.TextContent):
            try:
                return json.loads(block.text)
            except json.JSONDecodeError:
                return block.text
    raise RuntimeError(f"MCP tool {tool_name} returned no usable content")


async def call_proxy_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    return await call_mcp_tool(get_settings().mcp_proxy_url, tool_name, arguments)
