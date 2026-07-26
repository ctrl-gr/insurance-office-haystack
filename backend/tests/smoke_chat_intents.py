"""Manual chat intent smoke test; requires `python run_services.py`."""

import httpx


def send(message: str, session_id: str) -> str:
    response = httpx.post(
        f"http://127.0.0.1:5100/api/sessions/{session_id}/messages",
        json={"message": message},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["reply"]


def main() -> None:
    session = httpx.post(
        "http://127.0.0.1:5100/api/sessions",
        timeout=30,
    )
    session.raise_for_status()
    session_id = session.json()["sessionId"]

    quote_request = (
        "Compare car insurance for a 35 year old and a EUR 25,000 car"
    )
    quote_reply = send(quote_request, session_id)
    assert "The Blue Company" in quote_reply

    coverage_request = "Which coverage does the Blue car policy include?"
    coverage_reply = send(coverage_request, session_id)
    assert "Included:" in coverage_reply
    assert "Replacement car" in coverage_reply
    assert "The Lion Insurance" not in coverage_reply

    purchase_reply = send(
        "I want to purchase the Blue one",
        session_id,
    )
    assert "Purchase confirmed with The Blue Company" in purchase_reply
    assert "MCP-BLUE-" in purchase_reply
    print("quote, coverage, and purchase chat intents passed")


if __name__ == "__main__":
    main()
