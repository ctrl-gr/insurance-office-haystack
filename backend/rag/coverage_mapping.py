from __future__ import annotations

from typing import Literal


CoverageType = Literal["auto", "home", "life"]

SHARED_POLICY_CATEGORY: dict[CoverageType, str] = {
    "auto": "Car",
    "home": "Home",
    "life": "Injuries",
}


def category_for_coverage(coverage_type: CoverageType) -> str:
    return SHARED_POLICY_CATEGORY[coverage_type]
