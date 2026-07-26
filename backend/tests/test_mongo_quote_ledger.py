from copy import deepcopy
from types import SimpleNamespace

import pytest

from backend.config import get_settings
from backend.domain.mongo_quotes import MongoQuoteLedger


class MemoryCollection:
    def __init__(self):
        self.documents = {}

    def create_index(self, *args, **kwargs):
        return kwargs.get("name", "index")

    def insert_one(self, document):
        stored = deepcopy(document)
        self.documents[stored["_id"]] = stored
        return SimpleNamespace(inserted_id=stored["_id"])

    def find_one(self, filters):
        return next(
            (
                deepcopy(document)
                for document in self.documents.values()
                if self._matches(document, filters)
            ),
            None,
        )

    def find_one_and_update(
        self,
        filters,
        update,
        sort=None,
        return_document=None,
    ):
        candidates = [
            document
            for document in self.documents.values()
            if self._matches(document, filters)
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda item: item.get("created_at"), reverse=True)
        document = candidates[0]
        before = deepcopy(document)
        document.update(update.get("$set", {}))
        return before

    @staticmethod
    def _matches(document, filters):
        for key, expected in filters.items():
            actual = document.get(key)
            if isinstance(expected, dict) and "$gt" in expected:
                if actual is None or actual <= expected["$gt"]:
                    return False
            elif actual != expected:
                return False
        return True


def create_ledger(quotes, purchases):
    return MongoQuoteLedger(
        "blue",
        get_settings(),
        quotes_collection=quotes,
        purchases_collection=purchases,
    )


def test_mongo_quote_survives_ledger_recreation_and_is_session_bound():
    quotes = MemoryCollection()
    purchases = MemoryCollection()
    first_process = create_ledger(quotes, purchases)
    quote = first_process.issue(
        {"annualPremium": 1000.0},
        "session-one",
    )

    restarted_process = create_ledger(quotes, purchases)
    with pytest.raises(ValueError, match="No active issued quote"):
        restarted_process.consume(
            1000.0,
            "session-two",
            quote["quoteId"],
        )

    issued = restarted_process.consume(
        1000.0,
        "session-one",
        quote["quoteId"],
    )
    purchase = restarted_process.record_purchase(
        issued,
        {
            "reference": "MCP-BLUE-PERSISTED",
            "status": "confirmed",
            "amount": 1000.0,
        },
    )

    assert purchase["reference"] in purchases.documents
    assert purchases.documents[purchase["reference"]]["session_id"] == "session-one"
    assert quotes.documents[quote["quoteId"]]["status"] == "purchased"
