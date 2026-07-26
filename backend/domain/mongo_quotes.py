from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument
from pymongo.collection import Collection

from backend.config import Settings
from .quotes import IssuedQuote


def _premium_cents(value: float | Decimal) -> int:
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(amount * 100)


class MongoQuoteLedger:
    """Persistent, session-bound quote and purchase ledger shared by every MCP server."""

    def __init__(
        self,
        provider_id: str,
        settings: Settings,
        *,
        client: MongoClient | None = None,
        quotes_collection: Collection | None = None,
        purchases_collection: Collection | None = None,
    ):
        self.provider_id = provider_id
        self.ttl = timedelta(seconds=settings.quote_ttl_seconds)
        if quotes_collection is not None and purchases_collection is not None:
            self.client = client
            self.quotes = quotes_collection
            self.purchases = purchases_collection
        else:
            self.client = client or MongoClient(
                settings.mongodb_uri,
                serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
            )
            self.client.admin.command("ping")
            database = self.client[settings.mongodb_database]
            self.quotes = database[settings.mongodb_quotes_collection]
            self.purchases = database[settings.mongodb_purchases_collection]
        self.ensure_indexes()

    def ensure_indexes(self) -> None:
        self.quotes.create_index(
            [
                ("session_id", ASCENDING),
                ("provider_id", ASCENDING),
                ("status", ASCENDING),
                ("expires_at", ASCENDING),
            ],
            name="active_session_quotes",
        )
        self.quotes.create_index(
            [("session_id", ASCENDING), ("created_at", DESCENDING)],
            name="session_quote_history",
        )
        self.purchases.create_index(
            [("quote_id", ASCENDING)],
            unique=True,
            name="one_purchase_per_quote",
        )
        self.purchases.create_index(
            [("session_id", ASCENDING), ("created_at", DESCENDING)],
            name="session_purchase_history",
        )

    def issue(self, quote: dict, session_id: str) -> dict:
        if not session_id:
            raise ValueError("session_id is required")
        now = datetime.now(timezone.utc)
        expires_at = now + self.ttl
        quote_id = f"Q-{self.provider_id.upper().replace('-', '')}-{uuid.uuid4().hex[:12].upper()}"
        document = {
            "_id": quote_id,
            "session_id": session_id,
            "provider_id": self.provider_id,
            "annual_premium_cents": _premium_cents(quote["annualPremium"]),
            "status": "active",
            "created_at": now,
            "expires_at": expires_at,
            "quote": quote,
        }
        self.quotes.insert_one(document)
        return {**quote, "quoteId": quote_id, "expiresAt": expires_at.isoformat()}

    def consume(
        self,
        annual_premium: float,
        session_id: str,
        quote_id: str | None = None,
    ) -> IssuedQuote:
        now = datetime.now(timezone.utc)
        cents = _premium_cents(annual_premium)
        filters = {
            "session_id": session_id,
            "provider_id": self.provider_id,
            "annual_premium_cents": cents,
            "status": "active",
            "expires_at": {"$gt": now},
        }
        if quote_id:
            filters["_id"] = quote_id
        document = self.quotes.find_one_and_update(
            filters,
            {"$set": {"status": "purchased", "consumed_at": now}},
            sort=[("created_at", DESCENDING)],
            return_document=ReturnDocument.BEFORE,
        )
        if document is None:
            self._raise_purchase_error(session_id, annual_premium, quote_id)
        return IssuedQuote(
            quote_id=document["_id"],
            session_id=document["session_id"],
            provider_id=document["provider_id"],
            annual_premium=Decimal(document["annual_premium_cents"]) / 100,
            expires_at=document["expires_at"],
            consumed=True,
        )

    def record_purchase(self, issued: IssuedQuote, purchase: dict) -> dict:
        now = datetime.now(timezone.utc)
        self.purchases.insert_one(
            {
                "_id": purchase["reference"],
                "quote_id": issued.quote_id,
                "session_id": issued.session_id,
                "provider_id": issued.provider_id,
                "amount_cents": _premium_cents(purchase["amount"]),
                "status": purchase["status"],
                "created_at": now,
                "purchase": purchase,
            }
        )
        return purchase

    def _raise_purchase_error(
        self,
        session_id: str,
        annual_premium: float,
        quote_id: str | None,
    ) -> None:
        if not quote_id:
            raise ValueError("No active issued quote matches this purchase")
        quote = self.quotes.find_one(
            {"_id": quote_id, "provider_id": self.provider_id}
        )
        if quote is None or quote.get("session_id") != session_id:
            raise ValueError("No active issued quote matches this purchase")
        if quote.get("status") == "purchased":
            raise ValueError("This quote has already been purchased")
        if quote.get("annual_premium_cents") != _premium_cents(annual_premium):
            raise ValueError("The purchase premium does not match the issued quote")
        if quote.get("expires_at") <= datetime.now(timezone.utc):
            raise ValueError("This quote has expired")
        raise ValueError("No active issued quote matches this purchase")
