"""Manual chat intent smoke test; requires `python run_services.py`."""

import httpx


def send(message: str, history: list[dict[str, str]]) -> str:
    response = httpx.post(
        "http://127.0.0.1:5100/api/chat",
        json={"message": message, "history": history},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["reply"]


def main() -> None:
    history: list[dict[str, str]] = []
    quote_request = "Compare car insurance for a 35 year old and a €25,000 car"
    quote_reply = send(quote_request, history)
    assert "The Blue Company" in quote_reply
    history += [{"role": "user", "content": quote_request}, {"role": "assistant", "content": quote_reply}]

    coverage_request = "Which coverage does the Blue car policy include?"
    coverage_reply = send(coverage_request, history)
    assert "Included:" in coverage_reply
    assert "Replacement car" in coverage_reply
    assert "The Lion Insurance" not in coverage_reply
    history += [{"role": "user", "content": coverage_request}, {"role": "assistant", "content": coverage_reply}]

    purchase_reply = send("I want to purchase the Blue one", history)
    assert "Purchase confirmed with The Blue Company" in purchase_reply
    assert "MCP-BLUE-" in purchase_reply
    print("quote, coverage, and purchase chat intents passed")


if __name__ == "__main__":
    main()
