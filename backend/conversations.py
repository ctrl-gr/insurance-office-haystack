from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument
from pymongo.collection import Collection

from backend.config import Settings


class ConversationNotFoundError(LookupError):
    pass


class MongoConversationRepository:
    def __init__(
        self,
        settings: Settings,
        *,
        client: MongoClient | None = None,
    ):
        self.client = client or MongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
        )
        self.client.admin.command("ping")
        database = self.client[settings.mongodb_database]
        self.sessions: Collection = database[settings.mongodb_sessions_collection]
        self.messages: Collection = database[settings.mongodb_messages_collection]
        self.ensure_indexes()

    def ensure_indexes(self) -> None:
        self.sessions.create_index(
            [("updated_at", DESCENDING)],
            name="session_recent_activity",
        )
        self.messages.create_index(
            [("session_id", ASCENDING), ("sequence", ASCENDING)],
            unique=True,
            name="session_message_sequence",
        )

    def create_session(self) -> dict:
        now = datetime.now(timezone.utc)
        session_id = f"S-{uuid.uuid4().hex.upper()}"
        document = {
            "_id": session_id,
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "next_sequence": 0,
        }
        self.sessions.insert_one(document)
        return self._serialize_session(document)

    def get_session(self, session_id: str) -> dict:
        document = self.sessions.find_one({"_id": session_id, "status": "active"})
        if document is None:
            raise ConversationNotFoundError("Conversation session was not found")
        return self._serialize_session(document)

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        citations: list[dict] | None = None,
    ) -> dict:
        if role not in {"user", "assistant"}:
            raise ValueError("Message role must be user or assistant")
        now = datetime.now(timezone.utc)
        session = self.sessions.find_one_and_update(
            {"_id": session_id, "status": "active"},
            {"$inc": {"next_sequence": 1}, "$set": {"updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        if session is None:
            raise ConversationNotFoundError("Conversation session was not found")
        document = {
            "session_id": session_id,
            "sequence": session["next_sequence"],
            "role": role,
            "content": content,
            "citations": citations or [],
            "created_at": now,
        }
        result = self.messages.insert_one(document)
        return self._serialize_message({**document, "_id": result.inserted_id})

    def list_messages(self, session_id: str, limit: int = 100) -> list[dict]:
        self.get_session(session_id)
        cursor = (
            self.messages.find({"session_id": session_id})
            .sort("sequence", DESCENDING)
            .limit(limit)
        )
        return [self._serialize_message(document) for document in reversed(list(cursor))]

    def delete_session(self, session_id: str) -> None:
        result = self.sessions.delete_one({"_id": session_id})
        if result.deleted_count == 0:
            raise ConversationNotFoundError("Conversation session was not found")
        self.messages.delete_many({"session_id": session_id})

    @staticmethod
    def _serialize_session(document: dict) -> dict:
        return {
            "sessionId": document["_id"],
            "status": document["status"],
            "createdAt": document["created_at"].isoformat(),
            "updatedAt": document["updated_at"].isoformat(),
        }

    @staticmethod
    def _serialize_message(document: dict) -> dict:
        return {
            "id": str(document["_id"]),
            "sessionId": document["session_id"],
            "sequence": document["sequence"],
            "role": document["role"],
            "content": document["content"],
            "citations": document.get("citations", []),
            "createdAt": document["created_at"].isoformat(),
        }
