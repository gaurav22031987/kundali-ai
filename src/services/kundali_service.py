"""Orchestration layer joining location resolution and chart mathematics."""

from dataclasses import replace

from src.models import BirthDetails, KundaliChart
from src.services.divisional_chart_service import calculate_dashamsa_chart, calculate_navamsa_chart
from src.services.geocoding_service import resolve_place
from src.services.birth_data_service import normalize_place
from src.services.vedic_calculator import calculate_chart


def generate_kundali(details: BirthDetails) -> KundaliChart:
    """Resolve the birthplace, then calculate a deterministic Vedic chart."""
    d1_chart = calculate_chart(details, resolve_place(normalize_place(details.place_of_birth)))
    return replace(d1_chart, navamsa=calculate_navamsa_chart(d1_chart), dashamsa=calculate_dashamsa_chart(d1_chart))
