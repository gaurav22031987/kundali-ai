"""Tests for English/Hindi presentation-only localization."""

from src.localization.translations import planet_name, sign_name, t
from src.models import BirthDetails, Location
from src.services.ai_interpretation_service import build_interpretation_prompt
from src.services.vedic_calculator import calculate_chart


def test_english_and_hindi_translation_lookup():
    assert t("name", "en") == "Name"
    assert t("name", "hi") == "नाम"


def test_missing_hindi_key_falls_back_to_english_then_key():
    assert t("app_title", "unknown") == "Kundali AI"
    assert t("not_a_translation_key", "hi") == "not_a_translation_key"


def test_planet_zodiac_and_table_column_translation():
    assert planet_name("Sun", "hi") == "सूर्य"
    assert sign_name("Aries", "hi") == "मेष"
    assert t("planet", "hi") == "ग्रह"
    assert t("longitude", "hi") == "देशांतर"


def test_ai_prompt_contains_selected_language_instruction_and_payload_language():
    chart = calculate_chart(
        BirthDetails("Aditi Sharma", __import__("datetime").date(1990, 1, 1), __import__("datetime").time(12, 0), "Female", "New Delhi, India"),
        Location("New Delhi, India", 28.6139, 77.2090, "Asia/Kolkata"),
    )
    prompt = build_interpretation_prompt(chart, "hi")
    assert "Respond entirely in natural Hindi" in prompt
    assert '"language": "hi"' in prompt
