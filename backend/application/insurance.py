from __future__ import annotations

import asyncio
from decimal import Decimal, ROUND_HALF_UP

from backend.mcp_proxy.client import call_proxy_tool


COMPANY_TOOLS = {
    "lion": "thelion",
    "blue": "thebluecompany",
    "three-lines": "thethreelines",
}
PROVIDERS = [
    {"id": "lion", "name": "The Lion Insurance"},
    {"id": "blue", "name": "The Blue Company"},
    {"id": "three-lines", "name": "The Three Lines Insurance"},
]


async def compare_quotes(
    age: int,
    coverage_type: str,
    asset_value: float,
    session_id: str,
) -> dict:
    arguments = {
        "client_age": age,
        "coverage_type": coverage_type,
        "asset_value": asset_value,
        "session_id": session_id,
    }
    quotes = await asyncio.gather(
        *(call_proxy_tool(f"{company}_get_quote", arguments) for company in COMPANY_TOOLS.values())
    )
    quotes.sort(key=lambda quote: quote["annualPremium"])
    for rank, quote in enumerate(quotes, start=1):
        quote["rank"] = rank
    return {"quotes": quotes, "bestValueProviderId": quotes[0]["providerId"]}


async def coverage_details(coverage_type: str, provider_id: str | None = None) -> dict:
    companies = [COMPANY_TOOLS[provider_id]] if provider_id else list(COMPANY_TOOLS.values())
    details = await asyncio.gather(
        *(call_proxy_tool(f"{company}_check_coverage", {"coverage_type": coverage_type}) for company in companies)
    )
    return {"coverageType": coverage_type, "providers": details}


async def purchase_policy(
    provider_id: str,
    annual_premium: float,
    session_id: str,
    quote_id: str | None = None,
) -> dict:
    arguments = {"annual_premium": annual_premium, "session_id": session_id}
    if quote_id:
        arguments["quote_id"] = quote_id
    result = await call_proxy_tool(f"{COMPANY_TOOLS[provider_id]}_purchase_policy", arguments)
    amount = Decimal(str(result["amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    office_fee = (amount * Decimal("0.10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {**result, "officeFee": float(office_fee), "companyShare": float(amount - office_fee)}
