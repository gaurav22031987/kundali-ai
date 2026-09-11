"""Convert a user-entered birthplace into coordinates and an IANA timezone."""

import logging
import os

from geopy.geocoders import Nominatim

from src.models import Location

LOGGER = logging.getLogger(__name__)
COMMON_PLACE_FALLBACKS = {
    "delhi": ("Delhi, India", 28.6139, 77.2090, "Asia/Kolkata"),
    "new delhi": ("New Delhi, India", 28.6139, 77.2090, "Asia/Kolkata"),
    "mumbai": ("Mumbai, Maharashtra, India", 19.0760, 72.8777, "Asia/Kolkata"),
    "kolkata": ("Kolkata, West Bengal, India", 22.5726, 88.3639, "Asia/Kolkata"),
    "chennai": ("Chennai, Tamil Nadu, India", 13.0827, 80.2707, "Asia/Kolkata"),
    "bengaluru": ("Bengaluru, Karnataka, India", 12.9716, 77.5946, "Asia/Kolkata"),
    "bangalore": ("Bengaluru, Karnataka, India", 12.9716, 77.5946, "Asia/Kolkata"),
    "jaipur": ("Jaipur, Rajasthan, India", 26.9124, 75.7873, "Asia/Kolkata"),
}


class LocationResolutionError(ValueError):
    """Raised when a birthplace cannot be converted to chart coordinates."""



def _setting(name: str, default: str) -> str:
    """Read deployment configuration from environment first, then Streamlit secrets."""
    if value := os.getenv(name):
        return value
    try:
        import streamlit as st
        return str(st.secrets.get(name, default))
    except Exception:
        return default


def _fallback_location(place: str) -> Location | None:
    record = COMMON_PLACE_FALLBACKS.get(place.strip().casefold())
    return Location(*record) if record else None


def resolve_place(place: str) -> Location:
    """Look up a place through Nominatim and determine its timezone locally."""
    user_agent = _setting("GEOCODER_USER_AGENT", "KundaliAI/1.0")
    try:
        timeout = float(_setting("GEOCODER_TIMEOUT", "15"))
    except ValueError:
        timeout = 15.0
    geocoder = Nominatim(user_agent=user_agent, timeout=timeout)
    try:
        result = geocoder.geocode(place, exactly_one=True, language="en", timeout=timeout)
    except Exception as error:
        LOGGER.exception("Nominatim geocoding failed for place=%r timeout=%s user_agent=%r error_type=%s", place, timeout, user_agent, type(error).__name__)
        fallback = _fallback_location(place)
        if fallback:
            LOGGER.warning("Using common-place fallback for %r after geocoding failure", place)
            return fallback
        raise LocationResolutionError("place_network") from error
    if result is None:
        LOGGER.warning("Nominatim returned no result for place=%r", place)
        fallback = _fallback_location(place)
        if fallback:
            LOGGER.warning("Using common-place fallback for %r after no geocoding result", place)
            return fallback
        raise LocationResolutionError("place_not_found")

    try:
        from timezonefinder import TimezoneFinder
        timezone_name = TimezoneFinder().timezone_at(lat=result.latitude, lng=result.longitude)
    except Exception:
        LOGGER.exception("TimezoneFinder failed for place=%r latitude=%s longitude=%s", place, result.latitude, result.longitude)
        fallback = _fallback_location(place)
        if fallback:
            LOGGER.warning("Using common-place fallback for %r after timezone lookup failure", place)
            return fallback
        raise LocationResolutionError("timezone_not_found")
    if timezone_name is None:
        LOGGER.error("TimezoneFinder returned no timezone for place=%r latitude=%s longitude=%s", place, result.latitude, result.longitude)
        raise LocationResolutionError("timezone_not_found")
    return Location(result.address, float(result.latitude), float(result.longitude), timezone_name)
