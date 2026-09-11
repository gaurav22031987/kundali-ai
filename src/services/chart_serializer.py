"""Serialize deterministic chart results before passing them to presentation or AI."""

from src.models import KundaliChart
from src.services.career_analysis_service import build_career_analysis


def chart_to_payload(chart: KundaliChart) -> dict:
    """Return JSON-safe chart facts. This function performs no astrology calculations."""
    return {
        "birth_utc": chart.birth_utc.isoformat(),
        "location": {
            "name": chart.location.display_name,
            "latitude": chart.location.latitude,
            "longitude": chart.location.longitude,
            "timezone": chart.location.timezone_name,
        },
        "lagna": {"sign": chart.ascendant_sign, "longitude": chart.ascendant_longitude},
        "sun_sign": chart.sun_sign,
        "moon_sign": chart.moon_sign,
        "planets": [
            {"name": p.name, "longitude": p.longitude, "sign": p.sign, "house": p.house, "nakshatra": p.nakshatra, "pada": p.pada}
            for p in chart.planets
        ],
        "houses": [{"number": h.number, "sign": h.sign} for h in chart.houses],
        "current_dasha": {
            "mahadasha": {"lord": chart.current_mahadasha.lord, "start": chart.current_mahadasha.start.isoformat(), "end": chart.current_mahadasha.end.isoformat()},
            "antardasha": {"lord": chart.current_antardasha.lord, "start": chart.current_antardasha.start.isoformat(), "end": chart.current_antardasha.end.isoformat()},
        },
        "navamsa": None if chart.navamsa is None else {
            "lagna_sign": chart.navamsa.lagna_sign,
            "houses": [{"number": h.number, "sign": h.sign} for h in chart.navamsa.houses],
            "positions": [
                {"name": p.name, "d1_sign": p.d1_sign, "d1_degree": p.d1_degree, "d9_sign": p.d9_sign, "d9_house": p.d9_house, "vargottama": p.vargottama}
                for p in chart.navamsa.positions
            ],
        },
        "dashamsa": None if chart.dashamsa is None else {
            "lagna_sign": chart.dashamsa.lagna_sign,
            "houses": [{"number": h.number, "sign": h.sign} for h in chart.dashamsa.houses],
            "positions": [
                {"name": p.name, "d1_sign": p.d1_sign, "d1_degree": p.d1_degree, "d10_sign": p.sign, "d10_house": p.house}
                for p in chart.dashamsa.positions
            ],
        },
        "career_analysis": None if chart.dashamsa is None else build_career_analysis(chart),
    }
