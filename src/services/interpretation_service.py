"""Rule-based interpretation layer; it never computes astronomical facts."""

from src.models import KundaliChart


def build_life_area_interpretations(chart: KundaliChart) -> dict[str, str]:
    """Create conservative study prompts using only calculated chart facts."""
    by_name = {planet.name: planet for planet in chart.planets}
    return {
        "Career": f"The 10th house is {chart.houses[9].sign}; Saturn is in {by_name['Saturn'].sign} (house {by_name['Saturn'].house}).",
        "Finance": f"The 2nd house is {chart.houses[1].sign}; Jupiter is in {by_name['Jupiter'].sign} (house {by_name['Jupiter'].house}).",
        "Marriage": f"The 7th house is {chart.houses[6].sign}; Venus is in {by_name['Venus'].sign} (house {by_name['Venus'].house}).",
        "Health": f"The 6th house is {chart.houses[5].sign}; the Ascendant is {chart.ascendant_sign}.",
        "Education": f"The 4th house is {chart.houses[3].sign}; Mercury is in {by_name['Mercury'].sign} (house {by_name['Mercury'].house}).",
    }
