from backend.app.demo import detect_intent, extract_provider_id, extract_quote_request


def test_frontend_car_suggestion_is_understood():
    kind, age, value = extract_quote_request(
        "How much to insure with full coverage a €25,000 car for a 35 year-old?",
        [],
    )

    assert (kind, age, value) == ("auto", 35, 25_000)


def test_italian_home_request_is_understood():
    kind, age, value = extract_quote_request(
        "Confronta una polizza casa da 300.000 euro per una persona di 56 anni",
        [],
    )

    assert (kind, age, value) == ("home", 56, 300_000)


def test_follow_up_answers_are_combined_with_history():
    history = [
        {"role": "user", "content": "I need car insurance"},
        {"role": "assistant", "content": "What is your age?"},
        {"role": "user", "content": "35 years old"},
        {"role": "assistant", "content": "What value would you like to insure?"},
    ]

    assert extract_quote_request("€25,000", history) == ("auto", 35, 25_000)


def test_latest_message_controls_intent():
    assert detect_intent("Which coverage does the car policy include?") == "coverage"
    assert detect_intent("I want to purchase the Blue one") == "purchase"
    assert detect_intent("Compare the prices") == "quote"


def test_selected_provider_is_recognized():
    assert extract_provider_id("I want to buy The Blue Company quote") == "blue"
    assert extract_provider_id("Proceed with Three Lines") == "three-lines"
