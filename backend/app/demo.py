from __future__ import annotations

import re
from typing import Literal

from backend.application.insurance import coverage_details, compare_quotes, purchase_policy


def _number(value: str) -> float:
    cleaned = value.replace(" ", "")
    if "," in cleaned and "." in cleaned:
        decimal_separator = "," if cleaned.rfind(",") > cleaned.rfind(".") else "."
        thousands_separator = "." if decimal_separator == "," else ","
        cleaned = cleaned.replace(thousands_separator, "").replace(decimal_separator, ".")
    elif re.search(r"[.,]\d{3}$", cleaned):
        cleaned = cleaned.replace(",", "").replace(".", "")
    else:
        cleaned = cleaned.replace(",", ".")
    return float(cleaned)


def extract_quote_request(message: str, history: list[dict[str, str]]) -> tuple[str | None, int | None, float | None]:
    previous = " ".join(item.get("content", "") for item in history if item.get("role") == "user")
    text = f"{previous} {message}".lower()
    aliases = {
        "auto": ("auto", "car", "vehicle", "motor", "macchina", "automobile", "veicolo"),
        "home": ("home", "house", "property", "casa", "abitazione", "immobile"),
        "life": ("life", "vita"),
    }
    kind = next(
        (kind for kind, words in aliases.items() if any(re.search(rf"\b{re.escape(word)}\b", text) for word in words)),
        None,
    )
    age_match = re.search(r"\b(\d{2})\s*(?:years?[- ]?old|year[- ]?old|yo|anni|enne)\b", text)
    numbers = [_number(value) for value in re.findall(r"\b\d[\d.,]*\b", text)]
    age = int(age_match.group(1)) if age_match else next((int(value) for value in numbers if 18 <= value <= 99), None)
    currency_matches = re.findall(r"(?:EUR|€)\s*(\d[\d.,]*)|(\d[\d.,]*)\s*(?:EUR|€|euros?)(?:\b|$)", text, re.IGNORECASE)
    currency_values = [_number(left or right) for left, right in currency_matches]
    asset = max(currency_values, default=0) or max((value for value in numbers if value > 100), default=0)
    return kind, age, asset or None


def detect_intent(message: str) -> Literal["purchase", "coverage", "quote", "unknown"]:
    text = message.lower()
    if any(word in text for word in ("purchas", "purhcas", "buy", "proceed", "confirm", "acquist", "compra", "proced", "conferma", "choose", "select", "scegli")):
        return "purchase"
    if any(word in text for word in ("cover", "guarantee", "included", "excluded", "deductible", "copre", "copertura", "garanz", "inclus", "esclus", "franchigia")):
        return "coverage"
    if any(word in text for word in ("quote", "price", "premium", "cost", "preventiv", "prezzo", "premio", "costa", "compare", "confront")):
        return "quote"
    return "unknown"


def extract_provider_id(text: str) -> str | None:
    lower = text.lower()
    if "lion" in lower:
        return "lion"
    if "blue" in lower:
        return "blue"
    if "three lines" in lower or "three-lines" in lower or "tre linee" in lower:
        return "three-lines"
    return None


def _provider_from_conversation(message: str, history: list[dict[str, str]]) -> str | None:
    provider_id = extract_provider_id(message)
    if provider_id:
        return provider_id
    for item in reversed(history):
        if item.get("role") == "user" and (provider_id := extract_provider_id(item.get("content", ""))):
            return provider_id
    return None


def _premium_from_history(provider_id: str, history: list[dict[str, str]]) -> float | None:
    names = {"lion": "The Lion Insurance", "blue": "The Blue Company", "three-lines": "The Three Lines Insurance"}
    pattern = re.compile(rf"{re.escape(names[provider_id])}:\s*(?:EUR|€)?\s*([\d.,]+)\s*/year", re.IGNORECASE)
    for item in reversed(history):
        if item.get("role") == "assistant" and (match := pattern.search(item.get("content", ""))):
            return _number(match.group(1))
    return None


def _format_guarantee(guarantee: dict) -> str:
    limit = guarantee.get("limit")
    limit_text = f" (limit EUR {limit['amount']:,.0f})" if limit else ""
    terms_text = f" - {guarantee['terms']}" if guarantee.get("terms") else ""
    return f"{guarantee['name']}{limit_text}{terms_text}"


async def demo_reply(message: str, history: list[dict[str, str]]) -> str:
    kind, age, asset = extract_quote_request(message, history)
    intent = detect_intent(message)
    if intent == "purchase":
        provider_id = _provider_from_conversation(message, history)
        quote_result = await compare_quotes(age, kind, asset) if kind and age and asset else None
        if provider_id is None:
            return "Which quote would you like to purchase: Lion, Blue, or Three Lines?"
        premium = next((q["annualPremium"] for q in quote_result["quotes"] if q["providerId"] == provider_id), None) if quote_result else None
        premium = premium or _premium_from_history(provider_id, history)
        if premium is None:
            return "I need a completed quote before purchasing. Tell me the insurance type, age, and insured value."
        receipt = await purchase_policy(provider_id, premium)
        return f"Purchase confirmed with {receipt['companyName']}. Reference: {receipt['reference']}. Annual premium: EUR {receipt['amount']:,.2f}."
    if intent == "coverage":
        if not kind:
            return "Which policy coverage do you want to inspect: car, home, or life?"
        details = await coverage_details(kind, extract_provider_id(message))
        rows = []
        for item in details["providers"]:
            included = [_format_guarantee(g) for g in item["guarantees"] if g["status"] == "included"]
            excluded = [g["name"] for g in item["guarantees"] if g["status"] == "excluded"]
            rows.append(f"{item['companyName']} - Included: {', '.join(included)}. Excluded: {', '.join(excluded) or 'none listed'}.")
        return "\n\n".join(rows)
    if kind and age and asset:
        result = await compare_quotes(age, kind, asset)
        rows = [f"{q['rank']}. {q['companyName']}: EUR {q['annualPremium']:,.2f}/year" for q in result["quotes"]]
        return "Illustrative comparison:\n\n" + "\n".join(rows)
    if intent == "unknown" and not kind:
        return "I can compare quotes, explain policy coverage, or purchase a selected quote. What would you like to do?"
    if not kind:
        return "What would you like to insure: a car, a home, or your life?"
    if age is None:
        return "What is the insured person's age?"
    return "What value would you like to insure?"
