"""Validation rules for Kundali AI input."""

from datetime import date

from src.models import BirthDetails
from src.localization.translations import t

ALLOWED_GENDERS = {"Female", "Male", "Non-binary", "Prefer not to say"}


def validate_birth_details(details: BirthDetails, lang: str = "en") -> list[str]:
    """Return a list of messages for every invalid field."""
    errors: list[str] = []

    if len(details.name.strip()) < 2:
        errors.append(t("name_short", lang))
    if not details.name.replace(" ", "").replace("-", "").isalpha():
        errors.append(t("name_chars", lang))
    if details.date_of_birth > date.today():
        errors.append(t("dob_future", lang))
    if details.gender not in ALLOWED_GENDERS:
        errors.append(t("invalid_gender", lang))
    if len(details.place_of_birth.strip()) < 2:
        errors.append(t("place_short", lang))

    return errors
