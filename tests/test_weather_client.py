"""Open-Meteo client unit tests."""

from datetime import datetime
from typing import Any

import httpx
import pytest

from app.weather import client as weather_client
from app.weather.client import OpenMeteoClient, OpenMeteoClientError


def open_meteo_payload(**current_overrides: object) -> dict[str, Any]:
    """Return a raw Open-Meteo-like response payload."""

    current: dict[str, object] = {
        "time": "2026-04-29T10:00",
        "temperature_2m": 18.5,
        "precipitation": 0.0,
        "cloud_cover": 16,
        "wind_speed_10m": 14.0,
        "wind_gusts_10m": 22.0,
    }
    current.update(current_overrides)
    return {
        "current": current,
        "hourly": {
            "time": [
                "2026-04-29T08:00",
                "2026-04-29T10:00",
                "2026-04-29T12:00",
            ],
            "visibility": [8000, 24000, 18000],
            "cloud_cover": [20, 16, 25],
            "precipitation": [0.0, 0.0, 0.1],
            "wind_speed_10m": [12.0, 14.0, 16.0],
        },
    }


class FakeResponse:
    """Small httpx response double."""

    def __init__(self, payload: dict[str, Any]):
        self.payload = payload

    def raise_for_status(self) -> None:
        """Simulate a successful HTTP status."""

    def json(self) -> dict[str, Any]:
        """Return fake JSON payload."""

        return self.payload


class FakeHTTPXClient:
    """Context manager double for httpx.Client."""

    last_client: "FakeHTTPXClient | None" = None

    def __init__(self, timeout: float):
        self.timeout = timeout
        self.requests: list[tuple[str, dict[str, object]]] = []
        FakeHTTPXClient.last_client = self

    def __enter__(self) -> "FakeHTTPXClient":
        return self

    def __exit__(self, *_exc_info: object) -> bool:
        return False

    def get(self, base_url: str, params: dict[str, object]) -> FakeResponse:
        """Record request parameters and return fake response."""

        self.requests.append((base_url, params))
        return FakeResponse(open_meteo_payload())


class InvalidJsonResponse(FakeResponse):
    """Response double that fails JSON decoding."""

    def json(self) -> dict[str, Any]:
        """Raise the same error shape as a broken JSON response."""

        raise ValueError("invalid json")


class InvalidJsonHTTPXClient(FakeHTTPXClient):
    """HTTP client double that returns invalid JSON."""

    def get(self, base_url: str, params: dict[str, object]) -> InvalidJsonResponse:
        self.requests.append((base_url, params))
        return InvalidJsonResponse(open_meteo_payload())


class FailingHTTPXClient(FakeHTTPXClient):
    """HTTP client double that simulates a network failure."""

    def get(self, base_url: str, params: dict[str, object]) -> FakeResponse:
        self.requests.append((base_url, params))
        raise httpx.ConnectError("network down")


def test_get_current_weather_uses_open_meteo_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Client sends the expected Open-Meteo query parameters."""

    monkeypatch.setattr(weather_client.httpx, "Client", FakeHTTPXClient)
    client = OpenMeteoClient(base_url="https://weather.example.test", timeout_seconds=3)

    result = client.get_current_weather(latitude=55.75, longitude=37.62)

    fake_client = FakeHTTPXClient.last_client
    assert fake_client is not None
    assert fake_client.timeout == 3
    base_url, params = fake_client.requests[0]
    assert base_url == "https://weather.example.test"
    assert params["latitude"] == 55.75
    assert params["longitude"] == 37.62
    assert params["current"] == weather_client.CURRENT_PARAMS
    assert params["hourly"] == weather_client.HOURLY_PARAMS
    assert params["timezone"] == "auto"
    assert result["visibility_m"] == 24000.0


def test_normalize_payload_uses_current_visibility_when_present() -> None:
    """Current visibility takes precedence over hourly fallback data."""

    client = OpenMeteoClient(base_url="https://weather.example.test")

    result = client._normalize_payload(open_meteo_payload(visibility=30000))

    assert result["timestamp"] == datetime(2026, 4, 29, 10, 0)
    assert result["visibility_m"] == 30000.0
    assert result["cloud_cover_percent"] == 16.0
    assert result["precipitation_mm"] == 0.0
    assert result["wind_speed_kmh"] == 14.0
    assert result["wind_gusts_kmh"] == 22.0
    assert result["temperature_c"] == 18.5


def test_normalize_payload_without_hourly_visibility_keeps_none() -> None:
    """Missing visibility is normalized as None for availability scoring."""

    client = OpenMeteoClient(base_url="https://weather.example.test")
    payload = open_meteo_payload()
    payload["hourly"].pop("visibility")

    result = client._normalize_payload(payload)

    assert result["visibility_m"] is None


def test_get_current_weather_invalid_json_raises_client_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid JSON is converted to an application client error."""

    monkeypatch.setattr(weather_client.httpx, "Client", InvalidJsonHTTPXClient)
    client = OpenMeteoClient(base_url="https://weather.example.test")

    with pytest.raises(OpenMeteoClientError, match="invalid JSON"):
        client.get_current_weather(latitude=55.75, longitude=37.62)


def test_get_current_weather_http_error_raises_client_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Network errors are converted to an application client error."""

    monkeypatch.setattr(weather_client.httpx, "Client", FailingHTTPXClient)
    client = OpenMeteoClient(base_url="https://weather.example.test")

    with pytest.raises(OpenMeteoClientError, match="request failed"):
        client.get_current_weather(latitude=55.75, longitude=37.62)


def test_normalize_payload_unexpected_format_raises_client_error() -> None:
    """Missing required current fields fail with a clear client error."""

    client = OpenMeteoClient(base_url="https://weather.example.test")
    payload = open_meteo_payload()
    del payload["current"]["cloud_cover"]

    with pytest.raises(OpenMeteoClientError, match="unexpected format"):
        client._normalize_payload(payload)


def test_normalize_payload_without_current_raises_client_error() -> None:
    """Missing current data fails before creating a snapshot."""

    client = OpenMeteoClient(base_url="https://weather.example.test")

    with pytest.raises(OpenMeteoClientError, match="no current data"):
        client._normalize_payload({"hourly": {}})
