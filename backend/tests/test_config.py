from dataclasses import replace

from backend.config import get_settings


def test_gpt_56_chat_completions_disables_reasoning_for_function_tools():
    settings = replace(get_settings(), openai_model="gpt-5.6-terra", openai_reasoning_effort=None)

    assert settings.generation_kwargs == {"reasoning_effort": "none"}


def test_non_reasoning_model_does_not_receive_reasoning_parameter():
    settings = replace(get_settings(), openai_model="gpt-4.1-mini", openai_reasoning_effort=None)

    assert settings.generation_kwargs == {}
