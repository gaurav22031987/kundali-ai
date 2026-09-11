"""Deterministic tests for standard Vedic Navamsa (D9) mapping."""

from datetime import date, time

from src.models import BirthDetails, Location
from src.services.divisional_chart_service import (
    NAVAMSA_DIVISION,
    calculate_navamsa_chart,
    navamsa_sign,
    navamsa_sign_index,
)
from src.services.vedic_calculator import calculate_chart


def _d1_chart():
    return calculate_chart(
        BirthDetails("Aditi Sharma", date(1990, 1, 1), time(12, 0), "Female", "New Delhi, India"),
        Location("New Delhi, India", 28.6139, 77.2090, "Asia/Kolkata"),
    )


def test_navamsa_division_boundaries():
    assert navamsa_sign(0) == "Aries"
    assert navamsa_sign(NAVAMSA_DIVISION - 0.00001) == "Aries"
    assert navamsa_sign(NAVAMSA_DIVISION) == "Taurus"


def test_movable_sign_mapping_starts_from_same_sign():
    assert navamsa_sign(0) == "Aries"
    assert navamsa_sign(90) == "Cancer"


def test_fixed_sign_mapping_starts_from_ninth_sign():
    assert navamsa_sign(30) == "Capricorn"  # Taurus -> Capricorn
    assert navamsa_sign(120) == "Aries"  # Leo -> Aries


def test_dual_sign_mapping_starts_from_fifth_sign():
    assert navamsa_sign(60) == "Libra"  # Gemini -> Libra
    assert navamsa_sign(150) == "Capricorn"  # Virgo -> Capricorn


def test_navamsa_lagna_and_planet_house_mapping():
    d1 = _d1_chart()
    d9 = calculate_navamsa_chart(d1)
    assert d9.lagna_sign == navamsa_sign(d1.ascendant_longitude)
    assert len(d9.houses) == 12
    for planet in d9.positions:
        expected_index = navamsa_sign_index(next(p.longitude for p in d1.planets if p.name == planet.name))
        assert planet.d9_sign == d9.houses[(planet.d9_house - 1)].sign
        assert planet.d9_sign == ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces")[expected_index]


def test_vargottama_detection_matches_d1_and_d9_sign_equality():
    d1 = _d1_chart()
    d9 = calculate_navamsa_chart(d1)
    assert all(position.vargottama == (position.d1_sign == position.d9_sign) for position in d9.positions)
