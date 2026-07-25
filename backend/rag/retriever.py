from __future__ import annotations

import logging
from typing import Protocol

from haystack import Document, component

from backend.config import Settings
from .repository import MongoInsuranceConditionsRepository


logger = logging.getLogger(__name__)


class QueryEmbedder(Protocol):
    def embed_query(self, query: str) -> list[float]: ...


@component
class MongoInsuranceConditionsRetriever:
    """Haystack retriever backed by MongoDB text search with optional Atlas vector fusion."""

    def __init__(
        self,
        repository: MongoInsuranceConditionsRepository,
        settings: Settings,
        embedder: QueryEmbedder | None = None,
    ):
        self.repository = repository
        self.settings = settings
        self.embedder = embedder

    @component.output_types(documents=list[Document])
    def run(
        self,
        query: str,
        category: str | None = None,
        policy_name: str | None = None,
        top_k: int = 5,
    ) -> dict[str, list[Document]]:
        retrieval_mode = "text"
        fallback_reason = None
        if self.settings.rag_retrieval_mode == "hybrid" and self.embedder:
            try:
                rows = self.repository.hybrid_search(
                    query,
                    self.embedder.embed_query(query),
                    vector_index=self.settings.mongodb_vector_index,
                    category=category,
                    policy_name=policy_name,
                    top_k=top_k,
                    num_candidates=self.settings.rag_vector_candidates,
                    rrf_k=self.settings.rag_hybrid_rrf_k,
                )
                retrieval_mode = "hybrid"
            except Exception as error:
                fallback_reason = type(error).__name__
                logger.warning(
                    "Hybrid condition retrieval failed; falling back to MongoDB text search",
                    exc_info=True,
                )
                rows = self.repository.search(query, category, policy_name, top_k)
        else:
            rows = self.repository.search(query, category, policy_name, top_k)
        documents = [
            Document(
                id=row["id"],
                content=row["content"],
                score=row["score"],
                meta={
                    "policyId": row.get("policy_id"),
                    "policyMongoId": row["policy_mongo_id"],
                    "category": row["category"],
                    "policyName": row["name_conditions"],
                    "storageUrl": row["storage_url"],
                    "pageNumber": row["page_number"],
                    "chunkIndex": row["chunk_index"],
                    "source": row["source"],
                    "retrievalMode": retrieval_mode,
                    "retrievalFallbackReason": fallback_reason,
                },
            )
            for row in rows
        ]
        return {"documents": documents}
