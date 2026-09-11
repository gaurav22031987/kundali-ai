"""Deterministic Vedic chart calculations backed by Swiss Ephemeris."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import swisseph as swe

from src.models import BirthDetails, DashaPeriod, House, KundaliChart, Location, PlanetPosition

SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces")
NAKSHATRAS = ("Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati")
DASHA_ORDER = ("Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury")
DASHA_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}
PLANET_IDS = (("Sun", swe.SUN), ("Moon", swe.MOON), ("Mars", swe.MARS), ("Mercury", swe.MERCURY), ("Jupiter", swe.JUPITER), ("Venus", swe.VENUS), ("Saturn", swe.SATURN), ("Rahu", swe.TRUE_NODE))
NAKSHATRA_SPAN = 360 / 27
YEAR_DAYS = 365.2425


def _normalize(longitude: float) -> float:
    return longitude % 360


def sign_for(longitude: float) -> str:
    return SIGNS[int(_normalize(longitude) // 30)]


def nakshatra_for(longitude: float) -> tuple[str, int]:
    normalized = _normalize(longitude)
    index = int(normalized // NAKSHATRA_SPAN)
    offset = normalized % NAKSHATRA_SPAN
    return NAKSHATRAS[index], min(4, int(offset / (NAKSHATRA_SPAN / 4)) + 1)


def _julian_day(details: BirthDetails, location: Location) -> tuple[float, datetime]:
    local_time = datetime.combine(details.date_of_birth, details.time_of_birth, tzinfo=ZoneInfo(location.timezone_name))
    utc_time = local_time.astimezone(UTC)
    hour = utc_time.hour + utc_time.minute / 60 + utc_time.second / 3600
    return swe.julday(utc_time.year, utc_time.month, utc_time.day, hour), utc_time


def _planet_longitude(julian_day: float, planet_id: int) -> float:
    return _normalize(swe.calc_ut(julian_day, planet_id, swe.FLG_SIDEREAL | swe.FLG_SWIEPH)[0][0])


def _antardasha_timeline(lord: str, start: datetime) -> tuple[DashaPeriod, ...]:
    """Return the nine Antardashas that exactly fill one Mahadasha."""
    cursor = start
    start_index = DASHA_ORDER.index(lord)
    periods: list[DashaPeriod] = []
    for offset in range(len(DASHA_ORDER)):
        sub_lord = DASHA_ORDER[(start_index + offset) % len(DASHA_ORDER)]
        days = DASHA_YEARS[lord] * DASHA_YEARS[sub_lord] / 120 * YEAR_DAYS
        end = cursor + timedelta(days=days)
        periods.append(DashaPeriod(sub_lord, cursor, end))
        cursor = end
    return tuple(periods)


def vimshottari_mahadasha_timeline(moon_longitude: float, birth_utc: datetime) -> tuple[DashaPeriod, ...]:
    """Return the complete 120-year Vimshottari cycle containing the birth time.

    The birth Mahadasha is selected by the Moon's Nakshatra lord.  Its start is
    back-calculated from the Moon's exact fractional progress within that
    Nakshatra; consequently the time remaining at birth is mathematically exact
    within the chosen 365.2425-day dasha-year convention.
    """
    nakshatra_index = int(_normalize(moon_longitude) // NAKSHATRA_SPAN)
    first_lord = DASHA_ORDER[nakshatra_index % len(DASHA_ORDER)]
    elapsed = (_normalize(moon_longitude) % NAKSHATRA_SPAN) / NAKSHATRA_SPAN
    cursor = birth_utc - timedelta(days=DASHA_YEARS[first_lord] * elapsed * YEAR_DAYS)
    periods: list[DashaPeriod] = []
    index = (DASHA_ORDER.index(first_lord) + 1) % len(DASHA_ORDER)
    first_end = cursor + timedelta(days=DASHA_YEARS[first_lord] * YEAR_DAYS)
    periods.append(DashaPeriod(first_lord, cursor, first_end, _antardasha_timeline(first_lord, cursor)))
    cursor = first_end
    for _ in range(8):
        lord = DASHA_ORDER[index]
        end = cursor + timedelta(days=DASHA_YEARS[lord] * YEAR_DAYS)
        periods.append(DashaPeriod(lord, cursor, end, _antardasha_timeline(lord, cursor)))
        cursor, index = end, (index + 1) % len(DASHA_ORDER)
    return tuple(periods)


def _period_at(periods: tuple[DashaPeriod, ...], at: datetime) -> DashaPeriod:
    return next((period for period in periods if period.start <= at < period.end), periods[-1])


def calculate_chart(details: BirthDetails, location: Location, at: datetime | None = None) -> KundaliChart:
    """Calculate a Lahiri sidereal, whole-sign Vedic chart and current dashas."""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    julian_day, birth_utc = _julian_day(details, location)
    _, ascmc = swe.houses_ex(julian_day, location.latitude, location.longitude, b"W", swe.FLG_SIDEREAL)
    ascendant = _normalize(ascmc[0])
    asc_sign_index = int(ascendant // 30)
    raw = {name: _planet_longitude(julian_day, planet_id) for name, planet_id in PLANET_IDS}
    raw["Ketu"] = _normalize(raw["Rahu"] + 180)
    positions = []
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        longitude = raw[name]
        nakshatra, pada = nakshatra_for(longitude)
        sign_index = int(longitude // 30)
        positions.append(PlanetPosition(name, longitude, sign_for(longitude), longitude % 30, ((sign_index - asc_sign_index) % 12) + 1, nakshatra, pada))
    houses = tuple(House(i + 1, SIGNS[(asc_sign_index + i) % 12], _normalize((asc_sign_index + i) * 30)) for i in range(12))
    moment = (at or datetime.now(UTC)).astimezone(UTC)
    mahadashas = vimshottari_mahadasha_timeline(raw["Moon"], birth_utc)
    mahadasha = _period_at(mahadashas, moment)
    antardasha = _period_at(mahadasha.antardashas, moment)
    by_name = {planet.name: planet for planet in positions}
    return KundaliChart(birth_utc, location, ascendant, sign_for(ascendant), by_name["Moon"].sign, by_name["Sun"].sign, tuple(positions), houses, mahadashas, mahadasha, antardasha)
