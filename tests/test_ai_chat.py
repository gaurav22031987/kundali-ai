"""Tests for chart-grounded AI chat context and prompt behavior."""

from datetime import date, time

import pytest

from src.models import BirthDetails, Location
from src.services.ai_chat_service import build_chat_context, build_chat_prompt, chat_is_available, detect_language
from src.services.vedic_calculator import calculate_chart


def _details_and_chart():
    details = BirthDetails("Aditi Sharma", date(1990, 1, 1), time(12, 0), "Female", "New Delhi, India")
    chart = calculate_chart(details, Location("New Delhi, India", 28.6139, 77.2090, "Asia/Kolkata"))
    return details, chart


def test_chat_context_contains_required_deterministic_sections():
    details, chart = _details_and_chart()
    context = build_chat_context(chart, details)
    assert context["birth_details"]["name"] == "Aditi Sharma"
    assert context["d1"]["lagna"]["sign"] == chart.ascendant_sign
    assert len(context["planetary_positions"]) == 9
    assert context["current_dasha"]["mahadasha"]["lord"] == chart.current_mahadasha.lord


def test_hindi_and_english_chat_prompts_include_language_and_history():
    details, chart = _details_and_chart()
    context = build_chat_context(chart, details)
    history = [{"role": "user", "content": "Earlier question"}, {"role": "assistant", "content": "Earlier answer"}]
    english = build_chat_prompt(context, history, "Career?", "en")
    hindi = build_chat_prompt(context, history, "करियर?", "hi")
    assert "Respond entirely in English" in english
    assert "Respond entirely in natural Hindi" in hindi
    assert "Earlier question" in english


def test_missing_chart_handling_and_api_key_handling(monkeypatch):
    assert build_chat_context(None, None) is None
    with pytest.raises(ValueError):
        build_chat_prompt(None, [], "Question", "en")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert chat_is_available() is False


def test_conversation_history_is_preserved_in_prompt():
    details, chart = _details_and_chart()
    prompt = build_chat_prompt(build_chat_context(chart, details), [{"role": "assistant", "content": "Saved response"}], "Follow up", "en")
    assert "Saved response" in prompt


def test_question_language_detection_prioritizes_devanagari_and_hinglish():
    assert detect_language("मेरी नौकरी कब लगेगी?", "en") == "hi"
    assert detect_language("job kab milegi", "en") == "hi"
    assert detect_language("When is my next opportunity?", "hi") == "hi"
