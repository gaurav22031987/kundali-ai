"""Offline behavior tests for Cloud-safe birthplace lookup."""

import pytest

from src.services import geocoding_service
from src.services.geocoding_service import LocationResolutionError, resolve_place


class FailingNominatim:
    def __init__(self, **_):
        pass

    def geocode(self, **_):
        raise TimeoutError("simulated network timeout")


def test_common_place_fallback_handles_cloud_geocoding_failure(monkeypatch):
    monkeypatch.setattr(geocoding_service, "Nominatim", FailingNominatim)
    location = resolve_place("Delhi")
    assert location.latitude == 28.6139
    assert location.longitude == 77.2090
    assert location.timezone_name == "Asia/Kolkata"


def test_unlisted_place_keeps_existing_network_error_code(monkeypatch):
    monkeypatch.setattr(geocoding_service, "Nominatim", FailingNominatim)
    with pytest.raises(LocationResolutionError, match="place_network"):
        resolve_place("An Unknown Place")
