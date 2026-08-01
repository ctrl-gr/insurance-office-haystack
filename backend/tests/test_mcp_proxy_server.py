import asyncio

from backend.mcp_proxy import server as proxy_server
from backend.mcp_proxy.client import call_mcp_tool, discover_mcp_tools


def test_company_tool_registration_preserves_public_schemas():
    tools = asyncio.run(discover_mcp_tools(proxy_server.proxy))
    definitions = {tool.name: tool for tool in tools}

    expected_company_tools = set(proxy_server.COMPANY_TOOL_NAMES)
    assert expected_company_tools < definitions.keys()
    assert definitions["thelion_get_quote"].input_schema["required"] == [
        "client_age",
        "coverage_type",
        "asset_value",
        "session_id",
    ]
    assert definitions["thelion_check_coverage"].input_schema["required"] == [
        "coverage_type"
    ]
    assert definitions["thelion_purchase_policy"].input_schema["required"] == [
        "annual_premium",
        "session_id",
    ]


def test_generated_company_tools_route_to_their_own_service(monkeypatch):
    calls = []

    async def fake_call(url, tool_name, arguments):
        calls.append((url, tool_name, arguments))
        return {"url": url}

    monkeypatch.setattr(proxy_server, "call_mcp_tool", fake_call)

    async def scenario():
        for company_id in proxy_server.COMPANY_IDS:
            result = await call_mcp_tool(
                proxy_server.proxy,
                f"{company_id}_check_coverage",
                {"coverage_type": "auto"},
            )
            assert result == {"url": proxy_server.SERVICE_URLS[company_id]}

    asyncio.run(scenario())

    assert [call[1] for call in calls] == ["check_coverage"] * len(
        proxy_server.COMPANY_IDS
    )
    assert all(call[2]["coverage_type"] == "auto" for call in calls)
    assert all(call[2]["request_id"] for call in calls)
