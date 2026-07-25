from __future__ import annotations

from haystack import Document
from haystack.components.embedders import OpenAIDocumentEmbedder, OpenAITextEmbedder
from haystack.utils import Secret

from backend.config import Settings
from backend.tls import windows_trust_store


class InsuranceConditionEmbedder:
    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when RAG_RETRIEVAL_MODE=hybrid")
        if settings.rag_embedding_dimensions < 1:
            raise ValueError("RAG_EMBEDDING_DIMENSIONS must be positive")

        self.model = settings.rag_embedding_model
        common = {
            "api_key": Secret.from_token(settings.openai_api_key),
            "model": settings.rag_embedding_model,
            "dimensions": settings.rag_embedding_dimensions,
            "http_client_kwargs": windows_trust_store(),
        }
        self.document_embedder = OpenAIDocumentEmbedder(
            **common,
            batch_size=32,
            progress_bar=False,
            raise_on_failure=True,
        )
        self.query_embedder = OpenAITextEmbedder(**common)

    def embed_chunks(self, chunks: list[dict]) -> list[dict]:
        documents = [Document(content=chunk["content"]) for chunk in chunks]
        embedded = self.document_embedder.run(documents=documents)["documents"]
        return [
            {**chunk, "embedding": document.embedding}
            for chunk, document in zip(chunks, embedded, strict=True)
        ]

    def embed_query(self, query: str) -> list[float]:
        return self.query_embedder.run(text=query)["embedding"]
