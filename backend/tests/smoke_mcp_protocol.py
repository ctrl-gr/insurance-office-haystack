"""Non-mutating MCP 2026-07-28 smoke test; requires `python run_services.py`."""

import asyncio
import json

from mcp import Client

from backend.agent.mcp_toolset import build_mcp_toolset
from backend.mcp_protocol import MCP_PROTOCOL_VERSION
from backend.mcp_proxy.client import call_proxy_tool


SERVERS = {
    "lion": "http://127.0.0.1:5081/mcp",
    "blue": "http://127.0.0.1:5082/mcp",
    "three-lines": "http://127.0.0.1:5083/mcp",
    "conditions": "http://127.0.0.1:5084/mcp",
    "proxy": "http://127.0.0.1:5275/mcp",
}


async def main() -> None:
    for name, url in SERVERS.items():
        async with Client(url) as client:
            tools = await client.list_tools()
            assert client.protocol_version == MCP_PROTOCOL_VERSION
            print(
                f"{name}: protocol={client.protocol_version}, "
                f"tools={len(tools.tools)}"
            )

    coverage = await call_proxy_tool(
        "thelion_check_coverage",
        {"coverage_type": "auto"},
    )
    assert coverage["providerId"] == "lion"
    assert coverage["coverageType"] == "auto"

    toolset = build_mcp_toolset(
        SERVERS["proxy"],
        tool_names=["thebluecompany_check_coverage"],
    )
    bridge_result = json.loads(toolset[0].invoke(coverage_type="home"))
    assert bridge_result["providerId"] == "blue"
    assert bridge_result["coverageType"] == "home"
    print("MCP discovery, proxy routing, and Haystack bridge passed")


if __name__ == "__main__":
    asyncio.run(main())
