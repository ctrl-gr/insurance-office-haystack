from __future__ import annotations

from haystack import Pipeline

from backend.config import Settings
from .pdf_ingestion import build_ingestor
from .repository import MongoInsuranceConditionsRepository
from .retriever import MongoInsuranceConditionsRetriever


class InsuranceConditionsRag:
    def __init__(self, settings: Settings, repository: MongoInsuranceConditionsRepository | None = None):
        self.repository = repository or MongoInsuranceConditionsRepository(
            settings.mongodb_uri,
            settings.mongodb_database,
            settings.mongodb_policies_collection,
            settings.mongodb_chunks_collection,
            settings.mongodb_server_selection_timeout_ms,
        )
        if settings.conditions_auto_ingest:
            summary = build_ingestor(settings, self.repository).run()
            if summary.failed:
                raise RuntimeError(f"PDF ingestion failed for {summary.failed} policies")
        self.pipeline = Pipeline()
        self.pipeline.add_component("retriever", MongoInsuranceConditionsRetriever(self.repository))

    def search(
        self,
        query: str,
        category: str | None = None,
        policy_name: str | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        result = self.pipeline.run(
            {
                "retriever": {
                    "query": query,
                    "category": category,
                    "policy_name": policy_name,
                    "top_k": top_k,
                }
            }
        )
        return [
            {
                "conditionId": document.id,
                "content": document.content,
                "score": document.score,
                **document.meta,
            }
            for document in result["retriever"]["documents"]
        ]
