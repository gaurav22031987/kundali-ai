"""Deterministic Vedic divisional-chart calculations derived from D1 longitudes."""

from src.models import DashamsaChart, DivisionalPosition, House, KundaliChart, NavamsaChart
from src.services.vedic_calculator import SIGNS

NAVAMSA_DIVISION = 30 / 9  # 3 degrees 20 minutes
DASHAMSA_DIVISION = 3
MOVABLE_SIGNS = {0, 3, 6, 9}
FIXED_SIGNS = {1, 4, 7, 10}


def navamsa_sign_index(d1_longitude: float) -> int:
    """Return D9 sign index using the standard movable/fixed/dual rule."""
    normalized = d1_longitude % 360
    d1_sign_index = int(normalized // 30)
    division = min(8, int((normalized % 30) / NAVAMSA_DIVISION))
    if d1_sign_index in MOVABLE_SIGNS:
        start = d1_sign_index
    elif d1_sign_index in FIXED_SIGNS:
        start = (d1_sign_index + 8) % 12  # ninth sign, inclusive
    else:
        start = (d1_sign_index + 4) % 12  # fifth sign, inclusive
    return (start + division) % 12


def navamsa_sign(d1_longitude: float) -> str:
    return SIGNS[navamsa_sign_index(d1_longitude)]


def calculate_navamsa_chart(chart: KundaliChart) -> NavamsaChart:
    """Calculate D9 Lagna, whole-sign houses, and planet positions from D1 facts."""
    lagna_index = navamsa_sign_index(chart.ascendant_longitude)
    houses = tuple(House(i + 1, SIGNS[(lagna_index + i) % 12], ((lagna_index + i) % 12) * 30) for i in range(12))
    positions = []
    for planet in chart.planets:
        d9_index = navamsa_sign_index(planet.longitude)
        positions.append(
            DivisionalPosition(
                name=planet.name,
                d1_sign=planet.sign,
                d1_degree=planet.degree_in_sign,
                d9_sign=SIGNS[d9_index],
                d9_house=((d9_index - lagna_index) % 12) + 1,
                vargottama=planet.sign == SIGNS[d9_index],
            )
        )
    return NavamsaChart(SIGNS[lagna_index], houses, tuple(positions))


def dashamsa_sign_index(d1_longitude: float) -> int:
    """Return D10 sign index using standard Parashara odd/even sign rules."""
    normalized = d1_longitude % 360
    d1_sign_index = int(normalized // 30)
    division = min(9, int((normalized % 30) / DASHAMSA_DIVISION))
    # Zodiac sign numbers 1, 3, 5... are odd (zero-based indexes 0, 2, 4...).
    start = d1_sign_index if d1_sign_index % 2 == 0 else (d1_sign_index + 8) % 12
    return (start + division) % 12


def dashamsa_sign(d1_longitude: float) -> str:
    return SIGNS[dashamsa_sign_index(d1_longitude)]


def calculate_dashamsa_chart(chart: KundaliChart) -> DashamsaChart:
    """Calculate D10 Lagna, whole-sign houses, and planet positions from D1 facts."""
    lagna_index = dashamsa_sign_index(chart.ascendant_longitude)
    houses = tuple(House(i + 1, SIGNS[(lagna_index + i) % 12], ((lagna_index + i) % 12) * 30) for i in range(12))
    positions = []
    for planet in chart.planets:
        d10_index = dashamsa_sign_index(planet.longitude)
        positions.append(
            DivisionalPosition(
                name=planet.name,
                d1_sign=planet.sign,
                d1_degree=planet.degree_in_sign,
                d9_sign=SIGNS[d10_index],
                d9_house=((d10_index - lagna_index) % 12) + 1,
                vargottama=planet.sign == SIGNS[d10_index],
            )
        )
    return DashamsaChart(SIGNS[lagna_index], houses, tuple(positions))


SIGN_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}


def d1_seventh_lord_d9_placement(chart: KundaliChart, navamsa: NavamsaChart) -> DivisionalPosition:
    """Return the D9 placement of the ruler of the D1 seventh house."""
    seventh_lord = SIGN_LORDS[chart.houses[6].sign]
    return next(position for position in navamsa.positions if position.name == seventh_lord)
