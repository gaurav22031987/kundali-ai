"""Language preference persistence helpers must never reset a valid selection."""

from src.localization.language_state import normalize_language
from src.services.birth_data_service import normalize_place


def test_valid_hindi_language_code_is_preserved():
    assert normalize_language("hi") == "hi"
    assert normalize_language("en") == "en"


def test_invalid_or_missing_persisted_language_falls_back_to_english():
    assert normalize_language(None) == "en"
    assert normalize_language("fr") == "en"


def test_hindi_place_alias_is_normalized_only_for_geocoding():
    assert normalize_place("दिल्ली") == "Delhi"
    assert normalize_place("जयपुर") == "जयपुर"
