from fastapi import APIRouter, HTTPException

from backend.application.insurance import COMPANY_TOOLS, coverage_details, compare_quotes, purchase_policy
from backend.app.errors import UpstreamServiceError
from backend.app.schemas import CoverageType, PurchaseRequest, QuoteRequest


router = APIRouter(prefix="/api")


@router.post("/quotes")
async def quotes(request: QuoteRequest) -> dict:
    try:
        return await compare_quotes(request.age, request.coverageType, request.assetValue)
    except Exception as error:
        raise UpstreamServiceError("The insurance MCP proxy is unavailable.") from error


@router.get("/coverage/{coverage_type}")
async def coverage(coverage_type: CoverageType, provider_id: str | None = None) -> dict:
    if provider_id is not None and provider_id not in COMPANY_TOOLS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")
    try:
        return await coverage_details(coverage_type, provider_id)
    except Exception as error:
        raise UpstreamServiceError("The insurance MCP proxy is unavailable.") from error


@router.post("/purchase")
async def purchase(request: PurchaseRequest) -> dict:
    try:
        return await purchase_policy(request.providerId, request.annualPremium, request.quoteId)
    except Exception as error:
        raise UpstreamServiceError("The selected quote could not be purchased.") from error
