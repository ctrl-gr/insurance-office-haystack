from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


CoverageType = Literal["auto", "home", "life"]
ProviderId = Literal["lion", "blue", "three-lines"]


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=50)


class QuoteRequest(BaseModel):
    age: int = Field(ge=18, le=99)
    coverageType: CoverageType
    assetValue: float = Field(gt=0, le=100_000_000)


class PurchaseRequest(BaseModel):
    providerId: ProviderId
    annualPremium: float = Field(gt=0)
    quoteId: str | None = Field(default=None, min_length=1, max_length=100)
