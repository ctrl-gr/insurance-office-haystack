"""Manual end-to-end smoke test; requires `python run_services.py`."""

import asyncio

import httpx

from backend.mcp_proxy.client import call_proxy_tool


async def main() -> None:
    discovered = await call_proxy_tool("list_company_tools", {})
    assert len(discovered["tools"]) == 10

    conditions = await call_proxy_tool(
        "search_insurance_conditions",
        {"query": "theft exclusions", "coverage_type": "auto"},
    )
    assert conditions["resultCount"] >= 1
    assert conditions["matches"][0]["policyName"] == "SafeCar26.1"
    assert conditions["matches"][0]["pageNumber"] >= 1

    lion_quote = await call_proxy_tool(
        "thelion_get_quote",
        {"client_age": 35, "coverage_type": "auto", "asset_value": 25_000},
    )
    assert lion_quote["annualPremium"] == 1125.0
    assert lion_quote["quoteId"].startswith("Q-LION-")

    purchase = await call_proxy_tool(
        "thelion_purchase_policy",
        {"annual_premium": lion_quote["annualPremium"], "quote_id": lion_quote["quoteId"]},
    )
    assert purchase["status"] == "confirmed"
    assert purchase["quoteId"] == lion_quote["quoteId"]

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "http://127.0.0.1:5100/api/chat",
            json={"message": "Compare auto insurance for a 35 year old and a 25000 car", "history": []},
        )
        response.raise_for_status()
        payload = response.json()
        assert "The Lion Insurance" in payload["reply"]
        assert "The Blue Company" in payload["reply"]
        assert "The Three Lines Insurance" in payload["reply"]

        rag_response = await client.post(
            "http://127.0.0.1:5100/api/chat",
            json={
                "message": "According to the shared auto conditions, how long is a replacement car provided? Cite the source.",
                "history": [],
            },
        )
        rag_response.raise_for_status()
        rag_reply = rag_response.json()["reply"]
        assert "10" in rag_reply
        assert "SafeCar26.1" in rag_reply

    print("MCP proxy, RAG retrieval, verified purchase, and conversational API smoke test passed")


if __name__ == "__main__":
    asyncio.run(main())
