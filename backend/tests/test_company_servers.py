import pytest

from backend.mcp_servers.blue import SPEC as BLUE
from backend.mcp_servers.company import calculate_quote, coverage_for, purchase_for
from backend.mcp_servers.lion import SPEC as LION
from backend.mcp_servers.three_lines import SPEC as THREE_LINES


def test_original_auto_rates_are_preserved():
    quotes = [calculate_quote(spec, 35, "auto", 25_000) for spec in (LION, BLUE, THREE_LINES)]

    assert [quote["annualPremium"] for quote in quotes] == [1125.0, 1000.0, 1375.0]


def test_original_young_driver_factors_are_preserved():
    quotes = [calculate_quote(spec, 22, "auto", 20_000) for spec in (LION, BLUE, THREE_LINES)]

    assert [quote["annualPremium"] for quote in quotes] == [1260.0, 1080.0, 1430.0]


def test_each_company_owns_distinct_coverage():
    lion = coverage_for(LION, "life")
    blue = coverage_for(BLUE, "life")
    three_lines = coverage_for(THREE_LINES, "life")

    assert next(item for item in lion["guarantees"] if item["code"] == "critical_illness")["terms"] == "36 covered conditions"
    assert next(item for item in blue["guarantees"] if item["code"] == "critical_illness")["terms"] == "48 covered conditions"
    assert next(item for item in three_lines["guarantees"] if item["code"] == "critical_illness")["terms"] == "60 covered conditions"


def test_guarantees_have_structured_limits_statuses_and_deductibles():
    coverage = coverage_for(THREE_LINES, "home")
    liability = next(item for item in coverage["guarantees"] if item["code"] == "third_party_liability")
    terrorism = next(item for item in coverage["guarantees"] if item["code"] == "war_terrorism")

    assert liability["status"] == "included"
    assert liability["limit"] == {"amount": 5_000_000, "currency": "EUR"}
    assert terrorism["status"] == "excluded"
    assert coverage["deductible"] == {"amount": 100, "currency": "EUR", "basis": "per_claim"}


def test_quote_guarantees_are_derived_from_policy_catalog():
    quote = calculate_quote(BLUE, 35, "auto", 25_000)

    assert "coverages" not in quote
    assert all(item["status"] == "included" for item in quote["guarantees"])
    assert {item["code"] for item in quote["guarantees"]} == {
        "third_party_liability", "theft_fire", "natural_events", "windshield", "roadside_assistance", "replacement_car"
    }


def test_company_purchase_is_validated_and_confirmed():
    result = purchase_for(LION, 1_125)

    assert result["status"] == "confirmed"
    assert result["amount"] == 1125.0
    assert result["reference"].startswith("MCP-LION-")

    with pytest.raises(ValueError):
        purchase_for(LION, 0)
