from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

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
PROXY_TOOL_NAMES.append("search_insurance_conditions")


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


def _tool_result_payload(value: Any) -> dict | None:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    if isinstance(value, list):
        text = "".join(getattr(part, "text", "") for part in value)
        return _tool_result_payload(text)
    return None


def extract_citations(messages: list[ChatMessage]) -> list[dict]:
    citations: list[dict] = []
    seen: set[tuple[str, int, str]] = set()
    for message in messages:
        for tool_result in message.tool_call_results:
            if tool_result.error or tool_result.origin.tool_name != "search_insurance_conditions":
                continue
            payload = _tool_result_payload(tool_result.result)
            for match in payload.get("matches", []) if payload else []:
                if not isinstance(match, dict):
                    continue
                policy_name = match.get("policyName")
                page_number = match.get("pageNumber")
                source = match.get("source")
                if not isinstance(policy_name, str) or not isinstance(page_number, int) or not isinstance(source, str):
                    continue
                identity = (policy_name, page_number, source)
                if identity in seen:
                    continue
                seen.add(identity)
                citations.append(
                    {
                        "policyName": policy_name,
                        "pageNumber": page_number,
                        "url": match.get("storageUrl") if isinstance(match.get("storageUrl"), str) else None,
                        "source": source,
                    }
                )
    return citations


def run_agent_response(message: str, history: list[dict[str, str]]) -> dict:
    result = get_agent().run(messages=build_messages(message, history))
    reply = result["last_message"].text or "I couldn't produce a response. Please try again."
    return {"reply": reply, "citations": extract_citations(result.get("messages", []))}


def run_agent(message: str, history: list[dict[str, str]]) -> str:
    return run_agent_response(message, history)["reply"]
