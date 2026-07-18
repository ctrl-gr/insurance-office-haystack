from __future__ import annotations

from functools import lru_cache

from haystack.components.agents import Agent
from haystack.dataclasses import ChatMessage
from haystack_integrations.tools.mcp import MCPToolset, StreamableHttpServerInfo

from backend.config import get_settings
from .model_factory import create_chat_generator
from .prompt import SYSTEM_PROMPT


PROXY_TOOL_NAMES = [
    f"{company}_{tool}"
    for company in ("thelion", "thebluecompany", "thethreelines")
    for tool in ("get_quote", "check_coverage", "purchase_policy")
]


@lru_cache(maxsize=1)
def get_agent() -> Agent:
    settings = get_settings()
    toolset = MCPToolset(
        server_info=StreamableHttpServerInfo(url=settings.mcp_proxy_url),
        tool_names=PROXY_TOOL_NAMES,
        connection_timeout=10,
        invocation_timeout=30,
    )
    agent = Agent(
        chat_generator=create_chat_generator(settings),
        tools=toolset,
        system_prompt=SYSTEM_PROMPT,
        exit_conditions=["text"],
    )
    agent.warm_up()
    return agent


def build_messages(message: str, history: list[dict[str, str]]) -> list[ChatMessage]:
    messages: list[ChatMessage] = []
    for item in history[-40:]:
        if item.get("role") == "assistant":
            messages.append(ChatMessage.from_assistant(item.get("content", "")))
        elif item.get("role") == "user":
            messages.append(ChatMessage.from_user(item.get("content", "")))
    messages.append(ChatMessage.from_user(message))
    return messages


def run_agent(message: str, history: list[dict[str, str]]) -> str:
    result = get_agent().run(messages=build_messages(message, history))
    return result["last_message"].text or "I couldn't produce a response. Please try again."
