"""Tests that presentation and AI layers preserve deterministic chart facts."""

from datetime import UTC, date, datetime, time

from src.components.north_indian_chart import PLANET_ABBREVIATIONS, build_chart_svg, house_chart_data
from src.models import BirthDetails, Location
from src.services.ai_interpretation_service import build_interpretation_prompt
from src.services.chart_serializer import chart_to_payload
from src.services.divisional_chart_service import calculate_navamsa_chart
from src.services.vedic_calculator import calculate_chart


def _chart():
    details = BirthDetails("Aditi Sharma", date(1990, 1, 1), time(12, 0), "Female", "New Delhi, India")
    location = Location("New Delhi, India", 28.6139, 77.2090, "Asia/Kolkata")
    return calculate_chart(details, location, at=datetime(2025, 1, 1, tzinfo=UTC))


def test_house_chart_mapping_places_each_planet_in_its_calculated_house():
    chart = _chart()
    cells = house_chart_data(chart)
    assert cells[1]["lagna"] is True
    for planet in chart.planets:
        assert PLANET_ABBREVIATIONS[planet.name] in cells[planet.house]["planets"]
    assert all(cells[house.number]["sign"] == house.sign for house in chart.houses)


def test_svg_contains_house_sign_lagna_and_planet_facts():
    chart = _chart()
    svg = build_chart_svg(chart)
    assert "Lagna" in svg
    assert chart.houses[0].sign in svg
    assert "Su" in svg


def test_ai_prompt_contains_structured_chart_data_and_fact_guardrails():
    chart = _chart()
    chart = chart.__class__(
        chart.birth_utc, chart.location, chart.ascendant_longitude, chart.ascendant_sign,
        chart.moon_sign, chart.sun_sign, chart.planets, chart.houses, chart.mahadashas,
        chart.current_mahadasha, chart.current_antardasha, calculate_navamsa_chart(chart),
    )
    payload = chart_to_payload(chart)
    prompt = build_interpretation_prompt(chart)
    assert payload["lagna"]["sign"] == chart.ascendant_sign
    assert chart.planets[0].name in prompt
    assert chart.current_mahadasha.lord in prompt
    assert payload["navamsa"]["lagna_sign"] == chart.navamsa.lagna_sign
    assert "deterministic chart JSON" in prompt
