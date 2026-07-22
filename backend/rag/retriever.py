from __future__ import annotations

from haystack import Document, component

from .repository import MongoInsuranceConditionsRepository


@component
class MongoInsuranceConditionsRetriever:
    """Haystack sparse retriever backed by the MongoDB policy-chunks text index."""

    def __init__(self, repository: MongoInsuranceConditionsRepository):
        self.repository = repository

    @component.output_types(documents=list[Document])
    def run(
        self,
        query: str,
        category: str | None = None,
        policy_name: str | None = None,
        top_k: int = 5,
    ) -> dict[str, list[Document]]:
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
                },
            )
            for row in rows
        ]
        return {"documents": documents}
