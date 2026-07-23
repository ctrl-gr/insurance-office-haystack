from __future__ import annotations

from haystack.components.generators.chat import OpenAIChatGenerator

from backend.config import Settings
from backend.tls import windows_trust_store


def create_chat_generator(settings: Settings) -> OpenAIChatGenerator:
    return OpenAIChatGenerator(
        model=settings.openai_model,
        generation_kwargs=settings.generation_kwargs,
        http_client_kwargs=windows_trust_store(),
    )
