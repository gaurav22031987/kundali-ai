"""Deterministic tests for Parashara Dashamsa (D10) mapping and career facts."""

from dataclasses import replace
from datetime import date, time

from src.models import BirthDetails, Location
from src.services.career_analysis_service import build_career_analysis
from src.services.divisional_chart_service import (
    DASHAMSA_DIVISION,
    calculate_dashamsa_chart,
    dashamsa_sign,
)
from src.services.vedic_calculator import calculate_chart


def _d1_chart():
    return calculate_chart(
        BirthDetails("Aditi Sharma", date(1990, 1, 1), time(12, 0), "Female", "New Delhi, India"),
        Location("New Delhi, India", 28.6139, 77.2090, "Asia/Kolkata"),
    )


def test_d10_odd_sign_mapping_starts_from_same_sign():
    assert dashamsa_sign(0) == "Aries"
    assert dashamsa_sign(60) == "Gemini"


def test_d10_even_sign_mapping_starts_from_ninth_sign():
    assert dashamsa_sign(30) == "Capricorn"  # Taurus -> Capricorn
    assert dashamsa_sign(90) == "Pisces"  # Cancer -> Pisces


def test_d10_exact_three_degree_boundaries():
    assert dashamsa_sign(DASHAMSA_DIVISION - 0.00001) == "Aries"
    assert dashamsa_sign(DASHAMSA_DIVISION) == "Taurus"
    assert dashamsa_sign(30 + DASHAMSA_DIVISION - 0.00001) == "Capricorn"
    assert dashamsa_sign(30 + DASHAMSA_DIVISION) == "Aquarius"


def test_d10_lagna_and_planet_to_house_mapping():
    d1 = _d1_chart()
    d10 = calculate_dashamsa_chart(d1)
    assert d10.lagna_sign == dashamsa_sign(d1.ascendant_longitude)
    assert len(d10.positions) == 9
    for planet in d10.positions:
        assert planet.sign == d10.houses[planet.house - 1].sign


def test_d10_tenth_lord_identification_and_placement():
    d1 = _d1_chart()
    d10 = calculate_dashamsa_chart(d1)
    career = build_career_analysis(replace(d1, dashamsa=d10))
    lord = career["d10"]["tenth_lord"]
    assert lord in {planet.name for planet in d10.positions}
    assert career["d10"]["tenth_lord_house"] == next(planet.house for planet in d10.positions if planet.name == lord)
