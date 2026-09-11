"""Checks that Hindi presentation values never alter canonical chart inputs."""

from datetime import time

from src.services.birth_data_service import normalize_birth_data


def test_normalization_uses_canonical_date_and_english_enum_for_hindi_ui():
    details = normalize_birth_data("गौरव", 22, 3, 1987, time(1, 45), "Male", "Jaipur, Rajasthan, India")
    assert details.date_of_birth.isoformat() == "1987-03-22"
    assert details.time_of_birth == time(1, 45)
    assert details.gender == "Male"
    assert details.place_of_birth == "Jaipur, Rajasthan, India"
