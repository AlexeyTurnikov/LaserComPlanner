"""Availability scoring API tests."""

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.weather.router import get_weather_client


class FakeWeatherClient:
    """Fake Open-Meteo client for availability tests."""

    def __init__(self, payloads: list[dict[str, Any]] | None = None):
        self.payloads = payloads or [weather_payload()]
        self.calls: list[tuple[float, float]] = []

    def get_current_weather(
        self,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:
        """Return the next fake weather payload."""

        self.calls.append((latitude, longitude))
        if len(self.calls) <= len(self.payloads):
            return self.payloads[len(self.calls) - 1]
        return self.payloads[-1]


def weather_payload(**overrides: object) -> dict[str, Any]:
    """Return normalized weather data."""

    payload: dict[str, Any] = {
        "timestamp": datetime(2026, 4, 28, 10, 0, tzinfo=timezone.utc),
        "cloud_cover_percent": 10.0,
        "visibility_m": 25000.0,
        "precipitation_mm": 0.0,
        "wind_speed_kmh": 15.0,
        "wind_gusts_kmh": 20.0,
        "temperature_c": 16.0,
        "raw_payload": {"source": "mock-open-meteo"},
    }
    payload.update(overrides)
    return payload


def register_user(
    client: TestClient,
    email: str,
    password: str = "strongpass123",
) -> dict[str, object]:
    """Register a user through the public API."""

    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201
    return response.json()


def login_headers(
    client: TestClient,
    email: str,
    password: str = "strongpass123",
) -> dict[str, str]:
    """Return authorization headers for a user."""

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def auth_headers_for_role(client: TestClient, role: str) -> dict[str, str]:
    """Create a user with the requested role and return auth headers."""

    register_user(client, "admin@example.com")
    admin_headers = login_headers(client, "admin@example.com")
    if role == "admin":
        return admin_headers

    user = register_user(client, f"{role}@example.com")
    if role != "operator":
        response = client.patch(
            f"/api/v1/users/{user['id']}/role",
            json={"role": role},
            headers=admin_headers,
        )
        assert response.status_code == 200
    return login_headers(client, f"{role}@example.com")


def terminal_payload(**overrides: object) -> dict[str, object]:
    """Return a valid terminal payload."""

    payload: dict[str, object] = {
        "name": "Moscow Terminal",
        "latitude": 55.7558,
        "longitude": 37.6173,
        "altitude_m": 180,
        "status": "online",
        "max_data_rate_gbps": 20,
        "min_elevation_deg": 15,
    }
    payload.update(overrides)
    return payload


def create_terminal(
    client: TestClient,
    headers: Mapping[str, str],
    **overrides: object,
) -> dict[str, object]:
    """Create a terminal and return its response payload."""

    response = client.post(
        "/api/v1/terminals",
        json=terminal_payload(**overrides),
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def override_weather_client(fake_client: FakeWeatherClient) -> None:
    """Install a fake weather client dependency."""

    app.dependency_overrides[get_weather_client] = lambda: fake_client


def test_good_weather_gives_available(client: TestClient) -> None:
    """Good weather and online hardware produce available status."""

    operator_headers = auth_headers_for_role(client, "operator")
    admin_headers = login_headers(client, "admin@example.com")
    terminal = create_terminal(client, admin_headers)
    override_weather_client(FakeWeatherClient([weather_payload()]))

    response = client.post(
        f"/api/v1/availability/check/{terminal['id']}",
        headers=operator_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "available"
    assert payload["availability_score"] == 1.0
    assert "Visibility is sufficient" in payload["reason"]
    assert "Terminal hardware status is online" in payload["reason"]


def test_high_cloud_cover_gives_limited_or_unavailable(client: TestClient) -> None:
    """High cloud cover reduces availability."""

    headers = auth_headers_for_role(client, "operator")
    admin_headers = login_headers(client, "admin@example.com")
    terminal = create_terminal(client, admin_headers)
    override_weather_client(
        FakeWeatherClient([weather_payload(cloud_cover_percent=95.0)]),
    )

    response = client.post(
        f"/api/v1/availability/check/{terminal['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"limited", "unavailable"}
    assert payload["availability_score"] < 0.75
    assert "Cloud cover is too high" in payload["reason"]


def test_offline_terminal_gives_low_score(client: TestClient) -> None:
    """Offline hardware forces an unavailable result."""

    operator_headers = auth_headers_for_role(client, "operator")
    admin_headers = login_headers(client, "admin@example.com")
    terminal = create_terminal(client, admin_headers, status="offline")
    override_weather_client(FakeWeatherClient([weather_payload()]))

    response = client.post(
        f"/api/v1/availability/check/{terminal['id']}",
        headers=operator_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "unavailable"
    assert payload["availability_score"] < 0.5
    assert "Terminal hardware status is offline" in payload["reason"]


def test_missing_visibility_handled_correctly(client: TestClient) -> None:
    """Missing visibility uses a neutral score and explains it."""

    headers = auth_headers_for_role(client, "operator")
    admin_headers = login_headers(client, "admin@example.com")
    terminal = create_terminal(client, admin_headers)
    override_weather_client(FakeWeatherClient([weather_payload(visibility_m=None)]))

    response = client.post(
        f"/api/v1/availability/check/{terminal['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "available"
    assert payload["availability_score"] == 0.825
    assert "Visibility data is missing, neutral score applied" in payload["reason"]


def test_latest_check_returns_latest_result(client: TestClient) -> None:
    """Latest endpoint returns the most recent availability check."""

    engineer_headers = auth_headers_for_role(client, "engineer")
    operator_headers = engineer_headers
    terminal = create_terminal(client, engineer_headers)
    override_weather_client(
        FakeWeatherClient(
            [
                weather_payload(
                    timestamp=datetime(2026, 4, 28, 9, 0, tzinfo=timezone.utc),
                    cloud_cover_percent=95.0,
                ),
                weather_payload(
                    timestamp=datetime(2026, 4, 28, 11, 0, tzinfo=timezone.utc),
                    cloud_cover_percent=5.0,
                ),
            ],
        ),
    )

    client.post(f"/api/v1/weather/update/{terminal['id']}", headers=engineer_headers)
    client.post(f"/api/v1/availability/check/{terminal['id']}", headers=operator_headers)
    client.post(f"/api/v1/weather/update/{terminal['id']}", headers=engineer_headers)
    client.post(f"/api/v1/availability/check/{terminal['id']}", headers=operator_headers)

    response = client.get(
        f"/api/v1/availability/{terminal['id']}/latest",
        headers=operator_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "available"
    assert response.json()["availability_score"] == 1.0


def test_availability_map_returns_coordinates_and_statuses(
    client: TestClient,
) -> None:
    """Availability map includes terminal coordinates and latest weather summary."""

    operator_headers = auth_headers_for_role(client, "operator")
    admin_headers = login_headers(client, "admin@example.com")
    checked_terminal = create_terminal(client, admin_headers)
    empty_terminal = create_terminal(
        client,
        admin_headers,
        name="No Data Terminal",
        latitude=54.1961,
        longitude=37.6182,
    )
    override_weather_client(FakeWeatherClient([weather_payload(cloud_cover_percent=15.0)]))
    client.post(
        f"/api/v1/availability/check/{checked_terminal['id']}",
        headers=operator_headers,
    )

    response = client.get("/api/v1/availability-map", headers=operator_headers)

    assert response.status_code == 200
    payload = response.json()
    checked_item = next(
        item for item in payload if item["terminal_id"] == checked_terminal["id"]
    )
    empty_item = next(
        item for item in payload if item["terminal_id"] == empty_terminal["id"]
    )
    assert checked_item["latitude"] == checked_terminal["latitude"]
    assert checked_item["availability_status"] == "available"
    assert checked_item["cloud_cover_percent"] == 15.0
    assert empty_item["availability_status"] is None
    assert empty_item["weather_snapshot_id"] is None
