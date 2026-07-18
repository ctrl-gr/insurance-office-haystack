from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


GuaranteeStatus = Literal["included", "excluded", "optional"]


@dataclass(frozen=True)
class Money:
    amount: float
    currency: str = "EUR"

    def to_dict(self) -> dict:
        return {"amount": self.amount, "currency": self.currency}


@dataclass(frozen=True)
class Guarantee:
    code: str
    name: str
    description: str
    status: GuaranteeStatus = "included"
    limit: Money | None = None
    terms: str | None = None

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "limit": self.limit.to_dict() if self.limit else None,
            "terms": self.terms,
        }


@dataclass(frozen=True)
class Deductible:
    amount: Money
    basis: Literal["per_claim", "annual", "per_event"] = "per_claim"

    def to_dict(self) -> dict:
        return {**self.amount.to_dict(), "basis": self.basis}


@dataclass(frozen=True)
class PolicyCoverage:
    coverage_type: Literal["auto", "home", "life"]
    guarantees: tuple[Guarantee, ...]
    deductible: Deductible | None = None

    def included_guarantees(self) -> list[Guarantee]:
        return [guarantee for guarantee in self.guarantees if guarantee.status == "included"]

    def to_dict(self) -> dict:
        return {
            "coverageType": self.coverage_type,
            "guarantees": [guarantee.to_dict() for guarantee in self.guarantees],
            "deductible": self.deductible.to_dict() if self.deductible else None,
        }
