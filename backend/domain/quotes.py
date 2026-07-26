from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal


@dataclass
class IssuedQuote:
    quote_id: str
    session_id: str
    provider_id: str
    annual_premium: Decimal
    expires_at: datetime
    consumed: bool = False


class QuoteLedger:
    """Process-local ledger that prevents purchases without a previously issued quote."""

    def __init__(self, provider_id: str, ttl_seconds: int = 1800):
        self.provider_id = provider_id
        self.ttl = timedelta(seconds=ttl_seconds)
        self._quotes: dict[str, IssuedQuote] = {}
        self._lock = threading.Lock()

    def issue(self, quote: dict, session_id: str) -> dict:
        now = datetime.now(timezone.utc)
        issued = IssuedQuote(
            quote_id=f"Q-{self.provider_id.upper().replace('-', '')}-{uuid.uuid4().hex[:12].upper()}",
            session_id=session_id,
            provider_id=self.provider_id,
            annual_premium=Decimal(str(quote["annualPremium"])),
            expires_at=now + self.ttl,
        )
        with self._lock:
            self._purge(now)
            self._quotes[issued.quote_id] = issued
        return {**quote, "quoteId": issued.quote_id, "expiresAt": issued.expires_at.isoformat()}

    def consume(
        self,
        annual_premium: float,
        session_id: str,
        quote_id: str | None = None,
    ) -> IssuedQuote:
        now = datetime.now(timezone.utc)
        amount = Decimal(str(annual_premium))
        with self._lock:
            self._purge(now)
            if quote_id:
                candidate = self._quotes.get(quote_id)
                issued = candidate if candidate and candidate.session_id == session_id else None
            else:
                issued = next(
                    (
                        candidate
                        for candidate in reversed(tuple(self._quotes.values()))
                        if not candidate.consumed
                        and candidate.session_id == session_id
                        and candidate.annual_premium == amount
                    ),
                    None,
                )
            if issued is None:
                raise ValueError("No active issued quote matches this purchase")
            if issued.consumed:
                raise ValueError("This quote has already been purchased")
            if issued.annual_premium != amount:
                raise ValueError("The purchase premium does not match the issued quote")
            issued.consumed = True
            return issued

    def _purge(self, now: datetime) -> None:
        expired = [quote_id for quote_id, quote in self._quotes.items() if quote.expires_at <= now]
        for quote_id in expired:
            del self._quotes[quote_id]
