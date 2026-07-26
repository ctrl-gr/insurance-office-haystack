import json

from haystack.dataclasses import ChatMessage, ToolCall
from haystack.tools import Tool, Toolset

import backend.config as config
from backend.agent import build_messages
from backend.agent.service import (
    SESSION_SCOPED_TOOLS,
    extract_citations,
    hide_session_state_from_model,
)
from backend.config import get_settings


def test_build_messages_preserves_conversation_and_latest_question():
    history = [
        {"role": "user", "content": "I already have car insurance with Blue."},
        {"role": "assistant", "content": "What would you like to understand about it?"},
        {"role": "user", "content": "It includes collision coverage."},
    ]

    messages = build_messages("What exclusions should I check?", history)

    assert [message.role for message in messages] == [
        ChatMessage.from_user("").role,
        ChatMessage.from_assistant("").role,
        ChatMessage.from_user("").role,
        ChatMessage.from_user("").role,
    ]
    assert [message.text for message in messages] == [
        "I already have car insurance with Blue.",
        "What would you like to understand about it?",
        "It includes collision coverage.",
        "What exclusions should I check?",
    ]


def test_extract_citations_uses_condition_tool_results_and_deduplicates_sources():
    match = {
        "policyName": "SafeCar26.1",
        "pageNumber": 2,
        "storageUrl": "https://example.test/SafeCar26.1.pdf",
        "source": "SafeCar26.1#page-2-chunk-1",
    }
    message = ChatMessage.from_tool(
        json.dumps({"matches": [match, match], "resultCount": 2}),
        ToolCall(tool_name="search_insurance_conditions", arguments={"coverage_type": "auto"}),
    )

    assert extract_citations([message]) == [
        {
            "policyName": "SafeCar26.1",
            "pageNumber": 2,
            "url": "https://example.test/SafeCar26.1.pdf",
            "source": "SafeCar26.1#page-2-chunk-1",
        }
    ]


def test_quote_and_purchase_tools_receive_session_from_agent_state():
    assert set(SESSION_SCOPED_TOOLS) == {
        "thelion_get_quote",
        "thelion_purchase_policy",
        "thebluecompany_get_quote",
        "thebluecompany_purchase_policy",
        "thethreelines_get_quote",
        "thethreelines_purchase_policy",
    }
    assert all(
        mapping == {"session_id": "session_id"}
        for mapping in SESSION_SCOPED_TOOLS.values()
    )


def test_session_state_is_hidden_from_the_model_tool_schema():
    tool = Tool(
        name="thelion_get_quote",
        description="quote",
        parameters={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "client_age": {"type": "integer"},
            },
            "required": ["session_id", "client_age"],
        },
        function=lambda **kwargs: kwargs,
        inputs_from_state={"session_id": "session_id"},
    )
    toolset = Toolset([tool])

    hide_session_state_from_model(toolset)

    assert "session_id" not in tool.parameters["properties"]
    assert tool.parameters["required"] == ["client_age"]


def test_chat_is_unconfigured_without_key_or_explicit_demo(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ENV_FILE", tmp_path / "missing.env")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEMO_MODE", raising=False)

    get_settings.cache_clear()
    assert get_settings().chat_mode == "unconfigured"


def test_demo_mode_must_be_explicit(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ENV_FILE", tmp_path / "missing.env")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("DEMO_MODE", "true")

    get_settings.cache_clear()
    assert get_settings().chat_mode == "demo"


def test_api_key_selects_live_agent(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("DEMO_MODE", "true")

    get_settings.cache_clear()
    assert get_settings().chat_mode == "live"
