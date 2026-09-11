"""Tests for chart-grounded AI chat context and prompt behavior."""

import json
from datetime import date, time

from src.models import BirthDetails, Location
from src.services.ai_chat_service import (
    SYSTEM_PROMPT,
    _build_messages,
    build_chat_context,
    chat_is_available,
    detect_language,
)
from src.services.vedic_calculator import calculate_chart


def _details_and_chart():
    details = BirthDetails("Aditi Sharma", date(1990, 1, 1), time(12, 0), "Female", "New Delhi, India")
    chart = calculate_chart(details, Location("New Delhi, India", 28.6139, 77.2090, "Asia/Kolkata"))
    return details, chart


def test_chat_context_contains_deterministic_birth_and_chart_data():
    details, chart = _details_and_chart()
    context = json.loads(build_chat_context(chart, details))
    assert context["birth_details"]["name"] == "Aditi Sharma"
    assert context["calculated_chart"]["ascendant_sign"] == chart.ascendant_sign


def test_fallback_openai_messages_include_history_and_language():
    details, chart = _details_and_chart()
    messages = _build_messages(
        build_chat_context(chart, details),
        [{"role": "assistant", "content": "Saved response"}],
        "Follow up",
        "hi",
    )
    assert any("Hindi" in message["content"] for message in messages if message["role"] == "system")
    assert {"role": "assistant", "content": "Saved response"} in messages


def test_missing_api_key_disables_chat(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert chat_is_available() is False


def test_question_language_detection_prioritizes_devanagari_and_hinglish():
    assert detect_language("मेरी नौकरी कब लगेगी?", "en") == "hi"
    assert detect_language("job kab milegi", "en") == "hinglish"
    assert detect_language("When is my next opportunity?", "hi") == "hi"


def test_system_prompt_requires_one_relevant_follow_up_and_prior_history():
    assert "ask exactly ONE short follow-up" in SYSTEM_PROMPT
    assert "Do not repeat a clarification" in SYSTEM_PROMPT
    assert "answer the ORIGINAL user intent" in SYSTEM_PROMPT
