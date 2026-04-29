"""Routing and transmission planning API tests."""

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.weather.router import get_weather_client


class FakeWeatherClient:
    """Fake Open-Meteo client for availability setup."""

    def __init__(self, payload: dict[str, Any]):
        self.payload = payload

    def get_current_weather(
        self,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:
        """Return normalized fake weather."""

        return self.payload


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


def setup_users(client: TestClient) -> tuple[dict[str, str], dict[str, str]]:
    """Create admin and operator users and return their auth headers."""

    register_user(client, "admin@example.com")
    register_user(client, "operator@example.com")
    return (
        login_headers(client, "admin@example.com"),
        login_headers(client, "operator@example.com"),
    )


def terminal_payload(**overrides: object) -> dict[str, object]:
    """Return a valid terminal payload."""

    payload: dict[str, object] = {
        "name": "Source Terminal",
        "latitude": 0.0,
        "longitude": 0.0,
        "altitude_m": 100,
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


def create_link(
    client: TestClient,
    headers: Mapping[str, str],
    source_terminal_id: int,
    target_terminal_id: int,
    *,
    capacity_gbps: float = 10,
    is_active: bool = True,
) -> dict[str, object]:
    """Create a fiber link and return its response payload."""

    response = client.post(
        "/api/v1/fiber-links",
        json={
            "source_terminal_id": source_terminal_id,
            "target_terminal_id": target_terminal_id,
            "capacity_gbps": capacity_gbps,
            "is_active": is_active,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def create_availability(
    client: TestClient,
    headers: Mapping[str, str],
    terminal_id: int,
    payload: dict[str, Any],
) -> dict[str, object]:
    """Create an availability check using fake weather."""

    app.dependency_overrides[get_weather_client] = lambda: FakeWeatherClient(payload)
    response = client.post(
        f"/api/v1/availability/check/{terminal_id}",
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def transmission_payload(source_terminal_id: int, **overrides: object) -> dict[str, object]:
    """Return a valid transmission-plan payload."""

    payload: dict[str, object] = {
        "source_terminal_id": source_terminal_id,
        "data_volume_gb": 120,
        "priority": "high",
        "min_availability_score": 0.75,
    }
    payload.update(overrides)
    return payload


def test_source_terminal_available_returns_direct_route(client: TestClient) -> None:
    """An available source terminal uses direct satellite access."""

    admin_headers, operator_headers = setup_users(client)
    source = create_terminal(client, admin_headers)
    create_availability(client, operator_headers, source["id"], weather_payload())

    response = client.post(
        "/api/v1/routing/transmission-plan",
        json=transmission_payload(source["id"]),
        headers=operator_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["direct_satellite_access"] is True
    assert payload["recommended_terminal_id"] == source["id"]
    assert payload["route"] == [source["id"]]
    assert payload["route_distance_km"] == 0
    assert payload["final_score"] == 1.0


def test_source_unavailable_chooses_another_terminal(client: TestClient) -> None:
    """Planner chooses another available terminal when source is unavailable."""

    admin_headers, operator_headers = setup_users(client)
    source = create_terminal(client, admin_headers)
    target = create_terminal(
        client,
        admin_headers,
        name="Target Terminal",
        longitude=0.9,
    )
    create_link(client, admin_headers, source["id"], target["id"])
    create_availability(
        client,
        operator_headers,
        source["id"],
        weather_payload(cloud_cover_percent=95.0),
    )
    create_availability(client, operator_headers, target["id"], weather_payload())

    response = client.post(
        "/api/v1/routing/transmission-plan",
        json=transmission_payload(source["id"]),
        headers=operator_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["direct_satellite_access"] is False
    assert payload["recommended_terminal_id"] == target["id"]
    assert payload["route"] == [source["id"], target["id"]]
    assert payload["availability_score"] == 1.0


def test_choose_better_route_among_two_options(client: TestClient) -> None:
    """Planner prefers the reachable candidate with the better route score."""

    admin_headers, operator_headers = setup_users(client)
    source = create_terminal(client, admin_headers)
    near_target = create_terminal(
        client,
        admin_headers,
        name="Near Target",
        longitude=0.9,
    )
    far_target = create_terminal(
        client,
        admin_headers,
        name="Far Target",
        longitude=2.0,
    )
    create_link(client, admin_headers, source["id"], far_target["id"])
    create_link(client, admin_headers, source["id"], near_target["id"])
    create_availability(
        client,
        operator_headers,
        source["id"],
        weather_payload(cloud_cover_percent=95.0),
    )
    create_availability(client, operator_headers, near_target["id"], weather_payload())
    create_availability(client, operator_headers, far_target["id"], weather_payload())

    response = client.post(
        "/api/v1/routing/transmission-plan",
        json=transmission_payload(source["id"]),
        headers=operator_headers,
    )

    assert response.status_code == 200
    assert response.json()["recommended_terminal_id"] == near_target["id"]


def test_inactive_fiber_link_ignored(client: TestClient) -> None:
    """Inactive fiber links are ignored by route search."""

    admin_headers, operator_headers = setup_users(client)
    source = create_terminal(client, admin_headers)
    target = create_terminal(
        client,
        admin_headers,
        name="Target Terminal",
        longitude=0.9,
    )
    create_link(client, admin_headers, source["id"], target["id"], is_active=False)
    create_availability(
        client,
        operator_headers,
        source["id"],
        weather_payload(cloud_cover_percent=95.0),
    )
    create_availability(client, operator_headers, target["id"], weather_payload())

    response = client.post(
        "/api/v1/routing/transmission-plan",
        json=transmission_payload(source["id"]),
        headers=operator_headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "No route to any available terminal"


def test_no_route_returns_409(client: TestClient) -> None:
    """A reachable candidate is required when source is unavailable."""

    admin_headers, operator_headers = setup_users(client)
    source = create_terminal(client, admin_headers)
    target = create_terminal(
        client,
        admin_headers,
        name="Target Terminal",
        longitude=0.9,
    )
    create_availability(
        client,
        operator_headers,
        source["id"],
        weather_payload(cloud_cover_percent=95.0),
    )
    create_availability(client, operator_headers, target["id"], weather_payload())

    response = client.post(
        "/api/v1/routing/transmission-plan",
        json=transmission_payload(source["id"]),
        headers=operator_headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "No route to any available terminal"


def test_no_available_terminal_returns_409(client: TestClient) -> None:
    """At least one terminal must meet the availability threshold."""

    admin_headers, operator_headers = setup_users(client)
    source = create_terminal(client, admin_headers)
    create_availability(
        client,
        operator_headers,
        source["id"],
        weather_payload(cloud_cover_percent=95.0),
    )

    response = client.post(
        "/api/v1/routing/transmission-plan",
        json=transmission_payload(source["id"]),
        headers=operator_headers,
    )

    assert response.status_code == 409
    assert "No available terminals" in response.json()["detail"]


def test_final_score_calculated(client: TestClient) -> None:
    """Final score combines availability, route score, and capacity score."""

    admin_headers, operator_headers = setup_users(client)
    source = create_terminal(client, admin_headers)
    target = create_terminal(
        client,
        admin_headers,
        name="Target Terminal",
        longitude=0.9,
    )
    create_link(client, admin_headers, source["id"], target["id"], capacity_gbps=10)
    create_availability(
        client,
        operator_headers,
        source["id"],
        weather_payload(cloud_cover_percent=95.0),
    )
    create_availability(client, operator_headers, target["id"], weather_payload())

    response = client.post(
        "/api/v1/routing/transmission-plan",
        json=transmission_payload(source["id"], priority="high"),
        headers=operator_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    distance_penalty = abs(payload["route_distance_km"] - 100) / 100
    route_cost = (
        payload["route_distance_km"] * 0.5
        + payload["estimated_latency_ms"] * 0.3
        + distance_penalty * 0.2
    )
    route_score = 1 / (1 + route_cost / 100)
    expected_score = round(0.50 * 1.0 + 0.30 * route_score + 0.20 * 1.0, 4)
    assert payload["final_score"] == expected_score


def test_routing_result_saved(client: TestClient) -> None:
    """Transmission planning persists a routing result retrievable by request ID."""

    admin_headers, operator_headers = setup_users(client)
    source = create_terminal(client, admin_headers)
    target = create_terminal(
        client,
        admin_headers,
        name="Target Terminal",
        longitude=0.9,
    )
    create_link(client, admin_headers, source["id"], target["id"])
    create_availability(
        client,
        operator_headers,
        source["id"],
        weather_payload(cloud_cover_percent=95.0),
    )
    create_availability(client, operator_headers, target["id"], weather_payload())
    plan_response = client.post(
        "/api/v1/routing/transmission-plan",
        json=transmission_payload(source["id"]),
        headers=operator_headers,
    )
    request_id = plan_response.json()["request_id"]

    result_response = client.get(
        f"/api/v1/routing/results/{request_id}",
        headers=operator_headers,
    )

    assert result_response.status_code == 200
    payload = result_response.json()
    assert payload["request_id"] == request_id
    assert payload["selected_terminal_id"] == target["id"]
    assert payload["route_terminal_ids"] == [source["id"], target["id"]]
