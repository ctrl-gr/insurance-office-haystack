import pytest

from backend.domain import QuoteLedger


def test_quote_must_be_issued_before_it_can_be_consumed():
    ledger = QuoteLedger("blue")

    with pytest.raises(ValueError, match="No active issued quote"):
        ledger.consume(1000)


def test_issued_quote_can_be_consumed_only_once_at_its_exact_premium():
    ledger = QuoteLedger("blue")
    quote = ledger.issue({"annualPremium": 1000.0})

    with pytest.raises(ValueError, match="does not match"):
        ledger.consume(999.0, quote["quoteId"])

    issued = ledger.consume(1000.0, quote["quoteId"])
    assert issued.quote_id == quote["quoteId"]

    with pytest.raises(ValueError, match="already been purchased"):
        ledger.consume(1000.0, quote["quoteId"])
