import json

from haystack.dataclasses import ChatMessage, ToolCall

import backend.config as config
from backend.agent import build_messages
from backend.agent.service import extract_citations
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
