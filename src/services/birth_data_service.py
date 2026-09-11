"""Language-independent normalization before deterministic Kundali calculation."""

from datetime import date, time

from src.models import BirthDetails

HINDI_PLACE_ALIASES = {
    "दिल्ली": "Delhi",
    "नई दिल्ली": "New Delhi",
    "मुंबई": "Mumbai",
    "कोलकाता": "Kolkata",
    "चेन्नई": "Chennai",
    "बेंगलुरु": "Bengaluru",
}


def normalize_place(place: str) -> str:
    """Normalize a small set of common Hindi city aliases for geocoding only."""
    cleaned = place.strip()
    return HINDI_PLACE_ALIASES.get(cleaned, cleaned)


def normalize_birth_data(name: str, day: int, month: int, year: int, birth_time: time, gender: str, place: str) -> BirthDetails:
    """Convert UI primitives to canonical internal values without locale-dependent parsing."""
    return BirthDetails(
        name=name.strip(),
        date_of_birth=date(year, month, day),
        time_of_birth=birth_time,
        gender=gender,
        place_of_birth=place.strip(),
    )
