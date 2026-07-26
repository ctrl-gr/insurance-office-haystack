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
    sessionId: str | None = Field(
        default=None,
        min_length=34,
        max_length=34,
        pattern=r"^S-[A-F0-9]{32}$",
    )
    history: list[HistoryMessage] = Field(default_factory=list, max_length=50)


class SessionMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class QuoteRequest(BaseModel):
    age: int = Field(ge=18, le=99)
    coverageType: CoverageType
    assetValue: float = Field(gt=0, le=100_000_000)
    sessionId: str = Field(
        min_length=34,
        max_length=34,
        pattern=r"^S-[A-F0-9]{32}$",
    )


class PurchaseRequest(BaseModel):
    providerId: ProviderId
    annualPremium: float = Field(gt=0)
    sessionId: str = Field(
        min_length=34,
        max_length=34,
        pattern=r"^S-[A-F0-9]{32}$",
    )
    quoteId: str | None = Field(default=None, min_length=1, max_length=100)
