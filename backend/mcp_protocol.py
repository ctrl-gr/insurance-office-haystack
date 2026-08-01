"""Shared MCP 2026-07-28 protocol settings."""

from __future__ import annotations

from typing import Final


MCP_PROTOCOL_VERSION: Final = "2026-07-28"
MCP_SERVER_VERSION: Final = "1.0.0"


def streamable_http_options(port: int) -> dict[str, object]:
    """Return the sessionless HTTP configuration required by MCP 2026-07-28."""
    return {
        "transport": "streamable-http",
        "host": "127.0.0.1",
        "port": port,
        "stateless_http": True,
        "json_response": True,
    }
