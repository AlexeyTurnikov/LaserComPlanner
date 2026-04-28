"""Weather snapshot API tests."""

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.weather.client import OpenMeteoClientError
from app.weather.router import get_weather_client


class FakeWeatherClient:
    """Fake Open-Meteo client for endpoint tests."""

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


class FailingWeatherClient:
    """Fake client that simulates Open-Meteo failures."""

    def get_current_weather(
        self,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:
        """Raise the same error type as the real client."""

        raise OpenMeteoClientError("Open-Meteo request failed")


def weather_payload(**overrides: object) -> dict[str, Any]:
    """Return normalized weather data."""

    payload: dict[str, Any] = {
        "timestamp": datetime(2026, 4, 27, 10, 0, tzinfo=timezone.utc),
        "cloud_cover_percent": 12.0,
        "visibility_m": 25000.0,
        "precipitation_mm": 0.0,
        "wind_speed_kmh": 14.0,
        "wind_gusts_kmh": 22.0,
        "temperature_c": 18.5,
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


def override_weather_client(fake_client: object) -> None:
    """Install a fake weather client dependency."""

    app.dependency_overrides[get_weather_client] = lambda: fake_client


def test_mock_open_meteo_response_saves_weather_snapshot(
    client: TestClient,
) -> None:
    """Weather update saves a normalized mocked Open-Meteo response."""

    headers = auth_headers_for_role(client, "engineer")
    terminal = create_terminal(client, headers)
    fake_client = FakeWeatherClient()
    override_weather_client(fake_client)

    response = client.post(
        f"/api/v1/weather/update/{terminal['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["terminal_id"] == terminal["id"]
    assert payload["cloud_cover_percent"] == 12.0
    assert payload["visibility_m"] == 25000.0
    assert fake_client.calls == [(55.7558, 37.6173)]


def test_update_all_weather_saves_snapshots(client: TestClient) -> None:
    """Weather update-all saves one snapshot per terminal."""

    headers = auth_headers_for_role(client, "engineer")
    create_terminal(client, headers, name="Moscow Terminal")
    create_terminal(
        client,
        headers,
        name="Tula Terminal",
        latitude=54.1961,
        longitude=37.6182,
    )
    fake_client = FakeWeatherClient(
        [
            weather_payload(cloud_cover_percent=10.0),
            weather_payload(cloud_cover_percent=30.0),
        ],
    )
    override_weather_client(fake_client)

    response = client.post("/api/v1/weather/update-all", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert [item["cloud_cover_percent"] for item in payload] == [10.0, 30.0]


def test_latest_weather_returns_latest_snapshot(client: TestClient) -> None:
    """Latest endpoint returns the newest snapshot by timestamp."""

    engineer_headers = auth_headers_for_role(client, "engineer")
    register_user(client, "operator@example.com")
    operator_headers = login_headers(client, "operator@example.com")
    terminal = create_terminal(client, engineer_headers)
    fake_client = FakeWeatherClient(
        [
            weather_payload(
                timestamp=datetime(2026, 4, 27, 9, 0, tzinfo=timezone.utc),
                cloud_cover_percent=60.0,
            ),
            weather_payload(
                timestamp=datetime(2026, 4, 27, 11, 0, tzinfo=timezone.utc),
                cloud_cover_percent=5.0,
            ),
        ],
    )
    override_weather_client(fake_client)
    client.post(f"/api/v1/weather/update/{terminal['id']}", headers=engineer_headers)
    client.post(f"/api/v1/weather/update/{terminal['id']}", headers=engineer_headers)

    response = client.get(
        f"/api/v1/weather/{terminal['id']}/latest",
        headers=operator_headers,
    )

    assert response.status_code == 200
    assert response.json()["cloud_cover_percent"] == 5.0


def test_weather_history_returns_list(client: TestClient) -> None:
    """History endpoint returns snapshots in newest-first order."""

    engineer_headers = auth_headers_for_role(client, "engineer")
    register_user(client, "operator@example.com")
    operator_headers = login_headers(client, "operator@example.com")
    terminal = create_terminal(client, engineer_headers)
    fake_client = FakeWeatherClient(
        [
            weather_payload(
                timestamp=datetime(2026, 4, 27, 8, 0, tzinfo=timezone.utc),
                wind_speed_kmh=10.0,
            ),
            weather_payload(
                timestamp=datetime(2026, 4, 27, 12, 0, tzinfo=timezone.utc),
                wind_speed_kmh=20.0,
            ),
        ],
    )
    override_weather_client(fake_client)
    client.post(f"/api/v1/weather/update/{terminal['id']}", headers=engineer_headers)
    client.post(f"/api/v1/weather/update/{terminal['id']}", headers=engineer_headers)

    response = client.get(
        f"/api/v1/weather/{terminal['id']}/history",
        headers=operator_headers,
    )

    assert response.status_code == 200
    assert [item["wind_speed_kmh"] for item in response.json()] == [20.0, 10.0]


def test_weather_api_error_is_handled(client: TestClient) -> None:
    """Open-Meteo client errors are returned as 502 responses."""

    headers = auth_headers_for_role(client, "engineer")
    terminal = create_terminal(client, headers)
    override_weather_client(FailingWeatherClient())

    response = client.post(
        f"/api/v1/weather/update/{terminal['id']}",
        headers=headers,
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Open-Meteo request failed"
