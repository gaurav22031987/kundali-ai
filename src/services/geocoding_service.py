"""Convert a user-entered birthplace into coordinates and an IANA timezone."""

from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

from src.models import Location


class LocationResolutionError(ValueError):
    """Raised when a birthplace cannot be converted to chart coordinates."""


def resolve_place(place: str) -> Location:
    """Look up a place through OpenStreetMap and determine its timezone locally."""
    geocoder = Nominatim(user_agent="kundali-ai-streamlit")
    try:
        result = geocoder.geocode(place, exactly_one=True, language="en", timeout=10)
    except Exception as error:
        raise LocationResolutionError("place_network") from error
    if result is None:
        raise LocationResolutionError("place_not_found")

    timezone_name = TimezoneFinder().timezone_at(lat=result.latitude, lng=result.longitude)
    if timezone_name is None:
        raise LocationResolutionError("timezone_not_found")
    return Location(result.address, float(result.latitude), float(result.longitude), timezone_name)
