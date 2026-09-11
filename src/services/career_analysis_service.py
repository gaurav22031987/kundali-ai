"""Build deterministic D1/D10 career facts for display and AI interpretation."""

from src.models import KundaliChart
from src.services.divisional_chart_service import SIGN_LORDS


def build_career_analysis(chart: KundaliChart) -> dict:
    """Return only calculated career-relevant facts; this module makes no predictions."""
    if chart.dashamsa is None:
        raise ValueError("Dashamsa chart is required for career analysis.")
    d10 = chart.dashamsa
    d1_tenth = chart.houses[9]
    d1_lord = SIGN_LORDS[d1_tenth.sign]
    d1_planets = {planet.name: planet for planet in chart.planets}
    d1_lord_position = d1_planets[d1_lord]
    d10_tenth = d10.houses[9]
    d10_lord = SIGN_LORDS[d10_tenth.sign]
    d10_planets = {planet.name: planet for planet in d10.positions}
    d10_lord_position = d10_planets[d10_lord]
    return {
        "d1": {
            "lagna": chart.ascendant_sign,
            "tenth_house_sign": d1_tenth.sign,
            "tenth_lord": d1_lord,
            "tenth_lord_house": d1_lord_position.house,
            "planets_in_tenth": [planet.name for planet in chart.planets if planet.house == 10],
        },
        "d10": {
            "lagna": d10.lagna_sign,
            "tenth_house_sign": d10_tenth.sign,
            "tenth_lord": d10_lord,
            "tenth_lord_house": d10_lord_position.house,
            "planets_in_tenth": [planet.name for planet in d10.positions if planet.house == 10],
            "planet_positions": {planet.name: {"sign": planet.sign, "house": planet.house} for planet in d10.positions},
        },
        "dasha": {
            "current_mahadasha": chart.current_mahadasha.lord,
            "current_antardasha": chart.current_antardasha.lord,
        },
    }
