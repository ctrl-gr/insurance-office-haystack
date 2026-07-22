from __future__ import annotations

import re
from datetime import datetime, timezone

from pymongo import ASCENDING, TEXT, MongoClient, UpdateOne
from pymongo.collection import Collection


class MongoInsuranceConditionsRepository:
    def __init__(
        self,
        uri: str,
        database_name: str,
        policies_collection: str,
        chunks_collection: str,
        server_selection_timeout_ms: int = 5000,
        client: MongoClient | None = None,
    ):
        self.client = client or MongoClient(uri, serverSelectionTimeoutMS=server_selection_timeout_ms)
        self.client.admin.command("ping")
        database = self.client[database_name]
        self.policies: Collection = database[policies_collection]
        self.chunks: Collection = database[chunks_collection]
        self.ensure_indexes()

    def ensure_indexes(self) -> None:
        self.chunks.create_index(
            [("policy_mongo_id", ASCENDING), ("pdf_hash", ASCENDING), ("chunk_index", ASCENDING)],
            unique=True,
            name="policy_pdf_chunk_identity",
        )
        self.chunks.create_index(
            [("name_conditions", TEXT), ("content", TEXT)],
            weights={"name_conditions": 5, "content": 1},
            default_language="english",
            name="condition_chunk_text_search",
        )
        self.chunks.create_index(
            [("category", ASCENDING), ("name_conditions", ASCENDING)],
            name="condition_chunk_filters",
        )

    def list_policies(self) -> list[dict]:
        query = {
            "storage_url": {"$type": "string", "$ne": ""},
            "name_conditions": {"$type": "string", "$ne": ""},
        }
        return [
            {
                "policy_mongo_id": str(document["_id"]),
                "policy_id": document.get("id"),
                "category": document.get("category", "Unknown"),
                "name_conditions": document["name_conditions"],
                "storage_url": document["storage_url"],
                "indexed_pdf_hash": document.get("rag_indexed_pdf_hash"),
            }
            for document in self.policies.find(query)
        ]

    def replace_policy_chunks(self, policy: dict, pdf_hash: str, chunks: list[dict]) -> int:
        now = datetime.now(timezone.utc)
        operations = []
        for chunk in chunks:
            identity = {
                "policy_mongo_id": policy["policy_mongo_id"],
                "pdf_hash": pdf_hash,
                "chunk_index": chunk["chunk_index"],
            }
            document = {
                **identity,
                "policy_id": policy.get("policy_id"),
                "category": policy["category"],
                "name_conditions": policy["name_conditions"],
                "storage_url": policy["storage_url"],
                "page_number": chunk["page_number"],
                "content": chunk["content"],
                "content_hash": chunk["content_hash"],
                "source": chunk["source"],
                "indexed_at": now,
            }
            operations.append(UpdateOne(identity, {"$set": document}, upsert=True))
        if operations:
            self.chunks.bulk_write(operations, ordered=False)
        self.chunks.delete_many(
            {"policy_mongo_id": policy["policy_mongo_id"], "pdf_hash": {"$ne": pdf_hash}}
        )
        from bson import ObjectId

        self.policies.update_one(
            {"_id": ObjectId(policy["policy_mongo_id"])},
            {
                "$set": {
                    "rag_indexed_pdf_hash": pdf_hash,
                    "rag_indexed_at": now,
                    "rag_chunk_count": len(chunks),
                }
            },
        )
        return len(chunks)

    @staticmethod
    def build_filter(query: str, category: str | None, policy_name: str | None) -> dict:
        filters: dict = {"$text": {"$search": query}}
        if category:
            filters["category"] = {"$regex": f"^{re.escape(category)}$", "$options": "i"}
        if policy_name:
            filters["name_conditions"] = {"$regex": f"^{re.escape(policy_name)}$", "$options": "i"}
        return filters

    def search(
        self,
        query: str,
        category: str | None = None,
        policy_name: str | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        projection = {
            "policy_id": 1,
            "policy_mongo_id": 1,
            "category": 1,
            "name_conditions": 1,
            "storage_url": 1,
            "page_number": 1,
            "chunk_index": 1,
            "content": 1,
            "source": 1,
            "score": {"$meta": "textScore"},
        }
        cursor = (
            self.chunks.find(self.build_filter(query, category, policy_name), projection)
            .sort([("score", {"$meta": "textScore"})])
            .limit(top_k)
        )
        results = []
        for document in cursor:
            document_id = str(document.pop("_id"))
            results.append({**document, "id": document_id})
        return results
