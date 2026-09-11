"""Canonical language preference helpers, independent of chart calculation data."""

SUPPORTED_LANGUAGES = frozenset({"en", "hi"})


def normalize_language(value: object, default: str = "en") -> str:
    """Return only a supported language code, including for persisted URL values."""
    return value if isinstance(value, str) and value in SUPPORTED_LANGUAGES else default
