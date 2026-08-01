"""Haystack tools backed by the official MCP Python SDK v2 client."""

from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from typing import Any, Coroutine

from haystack.tools import Tool, Toolset

from backend.mcp_proxy.client import call_mcp_tool, discover_mcp_tools


def _run_async(operation: Coroutine[Any, Any, Any]) -> Any:
    """Run an MCP coroutine from Haystack's synchronous tool interface."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(operation)

    # A synchronous Tool may occasionally be invoked by a caller that already owns
    # an event loop. Isolate the MCP lifecycle rather than nesting asyncio.run().
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, operation).result()


def _model_result(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


def build_mcp_toolset(
    url: str,
    tool_names: list[str] | None = None,
    connection_timeout: float = 10,
    invocation_timeout: float = 30,
    inputs_from_state: dict[str, dict[str, str]] | None = None,
) -> Toolset:
    """Discover a modern MCP server and expose selected tools to Haystack."""
    definitions = _run_async(discover_mcp_tools(url, timeout=connection_timeout))
    available = {definition.name for definition in definitions}
    selected = set(tool_names) if tool_names is not None else available
    missing = selected - available
    if missing:
        raise RuntimeError(
            f"MCP tools not found: {', '.join(sorted(missing))}. "
            f"Available tools: {', '.join(sorted(available))}"
        )

    state_inputs = inputs_from_state or {}
    tools: list[Tool] = []
    for definition in definitions:
        if definition.name not in selected:
            continue

        def invoke_tool(
            _tool_name: str = definition.name,
            **arguments: Any,
        ) -> str:
            result = _run_async(
                call_mcp_tool(
                    url,
                    _tool_name,
                    arguments,
                    timeout=invocation_timeout,
                )
            )
            return _model_result(result)

        input_mapping = state_inputs.get(definition.name)
        tool = Tool(
            name=definition.name,
            description=definition.description or "",
            parameters=deepcopy(definition.input_schema),
            function=invoke_tool,
            inputs_from_state=input_mapping,
        )
        if input_mapping:
            properties = tool.parameters.get("properties", {})
            required = tool.parameters.get("required", [])
            for parameter_name in input_mapping.values():
                properties.pop(parameter_name, None)
                if parameter_name in required:
                    required.remove(parameter_name)
        tools.append(tool)

    return Toolset(tools)
