from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import logging
import time
from typing import Literal
import uuid

from mcp.server.fastmcp import FastMCP

from backend.config import get_settings
from backend.domain import QuoteLedger
from backend.mcp_audit import audit, get_audit_logger
from .coverage import PolicyCoverage

CoverageType = Literal["auto", "home", "life"]


@dataclass(frozen=True)
class CompanySpec:
    company_id: str
    company_name: str
    port: int
    auto_rate: Decimal
    auto_young_factor: Decimal
    auto_senior_factor: Decimal
    home_rate: Decimal
    life_rates: tuple[Decimal, Decimal, Decimal]
    coverages: dict[str, PolicyCoverage]
    standard_notes: dict[str, str]


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_quote(spec: CompanySpec, client_age: int, coverage_type: CoverageType, asset_value: float) -> dict:
    if not 18 <= client_age <= 99:
        raise ValueError("Age must be between 18 and 99")
    if coverage_type not in ("auto", "home", "life"):
        raise ValueError("Coverage type must be one of: auto, home, life")
    value = Decimal(str(asset_value))
    if value <= 0:
        raise ValueError("Asset value must be greater than 0")

    if coverage_type == "auto":
        factor = spec.auto_young_factor if client_age < 25 else spec.auto_senior_factor if client_age > 65 else Decimal("1")
        annual = _money(value * spec.auto_rate * factor)
        note = (
            f"Young driver surcharge applied (+{int((spec.auto_young_factor - 1) * 100)}%)"
            if client_age < 25
            else f"Senior driver surcharge applied (+{int((spec.auto_senior_factor - 1) * 100)}%)"
            if client_age > 65
            else spec.standard_notes["auto"]
        )
    elif coverage_type == "home":
        annual = _money(value * spec.home_rate)
        note = spec.standard_notes["home"]
    else:
        rate = spec.life_rates[0] if client_age < 40 else spec.life_rates[1] if client_age < 60 else spec.life_rates[2]
        annual = _money(value * rate)
        note = "Preferred rate (under 40)" if client_age < 40 else "Standard rate (40-59)" if client_age < 60 else "Senior rate (60+)"

    return {
        "providerId": spec.company_id,
        "companyName": spec.company_name,
        "coverageType": coverage_type,
        "annualPremium": float(annual),
        "monthlyPremium": float(_money(annual / Decimal("12"))),
        "guarantees": [guarantee.to_dict() for guarantee in spec.coverages[coverage_type].included_guarantees()],
        "notes": note,
    }


def coverage_for(spec: CompanySpec, coverage_type: CoverageType) -> dict:
    if coverage_type not in ("auto", "home", "life"):
        raise ValueError("Coverage type must be one of: auto, home, life")
    return {"providerId": spec.company_id, "companyName": spec.company_name, **spec.coverages[coverage_type].to_dict()}


def purchase_for(spec: CompanySpec, annual_premium: float) -> dict:
    amount = _money(Decimal(str(annual_premium)))
    if amount <= 0:
        raise ValueError("Annual premium must be greater than 0")
    return {
        "status": "confirmed",
        "reference": f"MCP-{spec.company_id.upper().replace('-', '')}-{int(amount * 100):08d}",
        "providerId": spec.company_id,
        "companyName": spec.company_name,
        "amount": float(amount),
    }


def create_company_server(spec: CompanySpec) -> FastMCP:
    server = FastMCP(spec.company_name, instructions=f"Insurance tools for {spec.company_name}.", host="127.0.0.1", port=spec.port, stateless_http=True, json_response=True)
    logger = get_audit_logger(spec.company_id)
    quote_ledger = QuoteLedger(spec.company_id, get_settings().quote_ttl_seconds)

    def execute(tool_name: str, request_id: str | None, operation) -> dict:
        trace_id = request_id or str(uuid.uuid4())
        started = time.perf_counter()
        audit(
            logger,
            spec.company_id,
            "tool.started",
            request_id=trace_id,
            company=spec.company_id,
            tool=tool_name,
        )
        try:
            result = operation()
            audit(
                logger,
                spec.company_id,
                "tool.completed",
                request_id=trace_id,
                company=spec.company_id,
                tool=tool_name,
                status="success",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            return result
        except Exception as error:
            audit(
                logger,
                spec.company_id,
                "tool.failed",
                level=logging.ERROR,
                request_id=trace_id,
                company=spec.company_id,
                tool=tool_name,
                status="error",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                error_type=type(error).__name__,
                error=str(error),
            )
            raise

    @server.tool(name="get_quote")
    def get_quote(client_age: int, coverage_type: CoverageType, asset_value: float, request_id: str | None = None) -> dict:
        """Get an illustrative insurance quote from this company."""
        return execute(
            "get_quote",
            request_id,
            lambda: quote_ledger.issue(calculate_quote(spec, client_age, coverage_type, asset_value)),
        )

    @server.tool(name="check_coverage")
    def check_coverage(coverage_type: CoverageType, request_id: str | None = None) -> dict:
        """Check included, excluded, and deductible details for a policy type."""
        return execute("check_coverage", request_id, lambda: coverage_for(spec, coverage_type))

    @server.tool(name="purchase_policy")
    def purchase_policy(annual_premium: float, quote_id: str | None = None, request_id: str | None = None) -> dict:
        """Purchase a previously issued active quote. quote_id is preferred when available."""
        def purchase_issued_quote() -> dict:
            issued = quote_ledger.consume(annual_premium, quote_id)
            return {**purchase_for(spec, annual_premium), "quoteId": issued.quote_id}

        return execute("purchase_policy", request_id, purchase_issued_quote)

    return server
