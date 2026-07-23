from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .service import InsuranceConditionsRag

__all__ = ["InsuranceConditionsRag"]


def __getattr__(name: str):
    if name == "InsuranceConditionsRag":
        from .service import InsuranceConditionsRag

        return InsuranceConditionsRag
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
