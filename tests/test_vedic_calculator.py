"""Fast offline checks for deterministic Vedic calculation helpers."""

from datetime import UTC, date, datetime, time, timedelta

from src.models import BirthDetails, Location
from src.services.vedic_calculator import (
    DASHA_YEARS,
    calculate_chart,
    format_dms,
    nakshatra_for,
    sign_for,
    vimshottari_mahadasha_timeline,
)


def test_sign_and_nakshatra_boundaries():
    assert sign_for(0) == "Aries"
    assert sign_for(359.9) == "Pisces"
    assert nakshatra_for(0) == ("Ashwini", 1)
    assert nakshatra_for(359.99)[0] == "Revati"
    assert format_dms(12 + 34 / 60 + 56 / 3600) == '12° 34\' 56"'


def test_chart_has_planets_houses_and_dashas():
    details = BirthDetails("Aditi Sharma", date(1990, 1, 1), time(12, 0), "Female", "New Delhi, India")
    location = Location("New Delhi, India", 28.6139, 77.2090, "Asia/Kolkata")
    chart = calculate_chart(details, location)
    assert len(chart.planets) == 9
    assert {planet.name for planet in chart.planets} == {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"}
    assert len(chart.houses) == 12
    assert 0 <= chart.ascendant_longitude < 360
    assert chart.ascendant_degree_dms.endswith('"')
    assert chart.ascendant_nakshatra
    assert chart.ascendant_pada in {1, 2, 3, 4}
    assert all(planet.degree_dms.endswith('"') for planet in chart.planets)
    assert all(isinstance(planet.is_retrograde, bool) for planet in chart.planets)
    assert chart.current_mahadasha.start < chart.current_mahadasha.end
    assert chart.current_antardasha.start < chart.current_antardasha.end


def test_vimshottari_cycle_is_120_years_with_nine_antardashas_each():
    birth = datetime(2000, 1, 1, tzinfo=UTC)
    timeline = vimshottari_mahadasha_timeline(0.0, birth)  # Ashwini: Ketu starts exactly at birth.

    assert [period.lord for period in timeline] == ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    assert timeline[0].start == birth
    assert len(timeline) == 9
    assert len(timeline[0].antardashas) == 9
    assert sum((period.end - period.start for period in timeline), timedelta()) == timedelta(days=120 * 365.2425)
    assert timeline[0].end - timeline[0].start == timedelta(days=DASHA_YEARS["Ketu"] * 365.2425)


def test_birth_nakshatra_progress_reduces_remaining_birth_mahadasha():
    birth = datetime(2000, 1, 1, tzinfo=UTC)
    # Midway through Ashwini means half of Ketu Mahadasha elapsed before birth.
    timeline = vimshottari_mahadasha_timeline((360 / 27) / 2, birth)
    ketu = timeline[0]
    assert ketu.lord == "Ketu"
    assert ketu.start == birth - timedelta(days=3.5 * 365.2425)
    assert ketu.end == birth + timedelta(days=3.5 * 365.2425)
