"""Open-Meteo API client."""

from datetime import datetime
from typing import Any

import httpx

from app.config import get_settings

CURRENT_PARAMS = (
    "temperature_2m,precipitation,cloud_cover,wind_speed_10m,wind_gusts_10m"
)
HOURLY_PARAMS = "visibility,cloud_cover,precipitation,wind_speed_10m"


class OpenMeteoClientError(Exception):
    """Raised when Open-Meteo data cannot be fetched or normalized."""


def _parse_datetime(value: str | None) -> datetime:
    """Parse an Open-Meteo timestamp."""

    if not value:
        return datetime.utcnow()
    normalized_value = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized_value)


def _nearest_hourly_value(
    payload: dict[str, Any],
    field_name: str,
    current_time: str | None,
) -> float | None:
    """Return the closest hourly value for a field."""

    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        return None

    values = hourly.get(field_name)
    if not isinstance(values, list) or not values:
        return None

    times = hourly.get("time")
    if not isinstance(times, list) or not times:
        first_value = values[0]
        return float(first_value) if first_value is not None else None

    current_dt = _parse_datetime(current_time)
    best_index = 0
    best_delta: float | None = None
    for index, timestamp in enumerate(times):
        try:
            candidate_delta = abs(
                (_parse_datetime(str(timestamp)) - current_dt).total_seconds(),
            )
        except ValueError:
            continue
        if best_delta is None or candidate_delta < best_delta:
            best_delta = candidate_delta
            best_index = index

    if best_index >= len(values):
        return None
    value = values[best_index]
    return float(value) if value is not None else None


class OpenMeteoClient:
    """Small synchronous client for Open-Meteo current weather data."""

    def __init__(self, base_url: str | None = None, timeout_seconds: float = 10.0):
        settings = get_settings()
        self.base_url = base_url or settings.open_meteo_base_url
        self.timeout_seconds = timeout_seconds

    def get_current_weather(
        self,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:
        """Fetch and normalize current weather for terminal coordinates."""

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": CURRENT_PARAMS,
            "hourly": HOURLY_PARAMS,
            "timezone": "auto",
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(self.base_url, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise OpenMeteoClientError("Open-Meteo request failed") from exc
        except ValueError as exc:
            raise OpenMeteoClientError("Open-Meteo returned invalid JSON") from exc

        return self._normalize_payload(payload)

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Normalize Open-Meteo response to the application weather shape."""

        current = payload.get("current")
        if not isinstance(current, dict):
            raise OpenMeteoClientError("Open-Meteo response has no current data")

        current_time = current.get("time")
        visibility = current.get("visibility")
        if visibility is None:
            visibility = _nearest_hourly_value(payload, "visibility", current_time)

        try:
            return {
                "timestamp": _parse_datetime(str(current_time) if current_time else None),
                "cloud_cover_percent": float(current["cloud_cover"]),
                "visibility_m": float(visibility) if visibility is not None else None,
                "precipitation_mm": float(current["precipitation"]),
                "wind_speed_kmh": float(current["wind_speed_10m"]),
                "wind_gusts_kmh": float(current["wind_gusts_10m"]),
                "temperature_c": float(current["temperature_2m"]),
                "raw_payload": payload,
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise OpenMeteoClientError(
                "Open-Meteo response has unexpected format",
            ) from exc
