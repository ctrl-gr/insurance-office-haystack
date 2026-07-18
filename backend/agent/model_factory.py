from __future__ import annotations

import ssl
import sys

from haystack.components.generators.chat import OpenAIChatGenerator

from backend.config import Settings


def windows_trust_store() -> dict:
    """Use Windows trusted roots while leaving HTTPS verification enabled."""
    if sys.platform != "win32" or not hasattr(ssl, "enum_certificates"):
        return {}
    context = ssl.create_default_context()
    roots = [
        ssl.DER_cert_to_PEM_cert(certificate)
        for certificate, encoding, _trust in ssl.enum_certificates("ROOT")
        if encoding == "x509_asn"
    ]
    if roots:
        context.load_verify_locations(cadata="".join(roots))
    return {"verify": context}


def create_chat_generator(settings: Settings) -> OpenAIChatGenerator:
    return OpenAIChatGenerator(
        model=settings.openai_model,
        generation_kwargs=settings.generation_kwargs,
        http_client_kwargs=windows_trust_store(),
    )
