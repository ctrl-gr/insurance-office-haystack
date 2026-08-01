import asyncio
import json

from mcp import Client
from mcp.server import MCPServer

from backend.agent.mcp_toolset import build_mcp_toolset
from backend.agent.service import hide_session_state_from_model
from backend.mcp_protocol import MCP_PROTOCOL_VERSION
from backend.mcp_proxy.client import call_mcp_tool, discover_mcp_tools


def _test_server() -> MCPServer:
    server = MCPServer("protocol-test", version="1.0.0")

    @server.tool(name="get_quote")
    def get_quote(client_age: int, session_id: str) -> dict:
        """Return a small quote fixture."""
        return {"clientAge": client_age, "sessionId": session_id}

    return server


def test_client_negotiates_2026_protocol_and_calls_structured_tool():
    server = _test_server()

    async def scenario() -> None:
        async with Client(server) as client:
            assert client.protocol_version == MCP_PROTOCOL_VERSION

        definitions = await discover_mcp_tools(server)
        assert [definition.name for definition in definitions] == ["get_quote"]
        assert definitions[0].input_schema["required"] == ["client_age", "session_id"]

        result = await call_mcp_tool(
            server,
            "get_quote",
            {"client_age": 35, "session_id": "S-TEST"},
        )
        assert result == {"clientAge": 35, "sessionId": "S-TEST"}

    asyncio.run(scenario())


def test_native_haystack_bridge_preserves_agent_state_mapping():
    toolset = build_mcp_toolset(
        _test_server(),
        tool_names=["get_quote"],
        inputs_from_state={"get_quote": {"session_id": "session_id"}},
    )

    hide_session_state_from_model(toolset)
    tool = toolset[0]

    assert "session_id" not in tool.parameters["properties"]
    assert tool.parameters["required"] == ["client_age"]
    assert json.loads(tool.invoke(client_age=42, session_id="S-BRIDGE")) == {
        "clientAge": 42,
        "sessionId": "S-BRIDGE",
    }
