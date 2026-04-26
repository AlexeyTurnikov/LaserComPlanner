"""Fiber link CRUD and distance calculation tests."""

from collections.abc import Mapping

from fastapi.testclient import TestClient


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


def terminal_payload(
    *,
    name: str,
    latitude: float,
    longitude: float,
) -> dict[str, object]:
    """Return a valid terminal payload."""

    return {
        "name": name,
        "latitude": latitude,
        "longitude": longitude,
        "altitude_m": 100,
        "status": "online",
        "max_data_rate_gbps": 20,
        "min_elevation_deg": 15,
    }


def create_terminal(
    client: TestClient,
    headers: Mapping[str, str],
    *,
    name: str,
    latitude: float = 0,
    longitude: float = 0,
) -> dict[str, object]:
    """Create a terminal through the public API."""

    response = client.post(
        "/api/v1/terminals",
        json=terminal_payload(name=name, latitude=latitude, longitude=longitude),
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def create_link(
    client: TestClient,
    headers: Mapping[str, str],
    source_terminal_id: int,
    target_terminal_id: int,
    capacity_gbps: float = 10,
    is_active: bool = True,
) -> dict[str, object]:
    """Create a fiber link through the public API."""

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


def create_terminal_pair(
    client: TestClient,
    headers: Mapping[str, str],
    target_longitude: float,
) -> tuple[dict[str, object], dict[str, object]]:
    """Create two terminals on the equator for predictable distance tests."""

    source = create_terminal(client, headers, name="Source Terminal")
    target = create_terminal(
        client,
        headers,
        name="Target Terminal",
        longitude=target_longitude,
    )
    return source, target


def test_create_fiber_link(client: TestClient) -> None:
    """Engineer users can create fiber links."""

    headers = auth_headers_for_role(client, "engineer")
    source, target = create_terminal_pair(client, headers, target_longitude=0.9)

    link = create_link(client, headers, source["id"], target["id"])

    assert link["source_terminal_id"] == source["id"]
    assert link["target_terminal_id"] == target["id"]
    assert link["capacity_gbps"] == 10
    assert link["is_active"] is True


def test_source_equal_target_returns_422(client: TestClient) -> None:
    """A fiber link cannot connect a terminal to itself."""

    headers = auth_headers_for_role(client, "engineer")
    source = create_terminal(client, headers, name="Source Terminal")

    response = client.post(
        "/api/v1/fiber-links",
        json={
            "source_terminal_id": source["id"],
            "target_terminal_id": source["id"],
            "capacity_gbps": 10,
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_distance_is_calculated(client: TestClient) -> None:
    """Distance is calculated with the Haversine formula."""

    headers = auth_headers_for_role(client, "engineer")
    source, target = create_terminal_pair(client, headers, target_longitude=0.9)

    link = create_link(client, headers, source["id"], target["id"])

    assert abs(link["distance_km"] - 100.075) < 0.01


def test_latency_is_calculated(client: TestClient) -> None:
    """Latency follows the distance / 200000 * 1000 formula."""

    headers = auth_headers_for_role(client, "engineer")
    source, target = create_terminal_pair(client, headers, target_longitude=0.9)

    link = create_link(client, headers, source["id"], target["id"])
    expected_latency = link["distance_km"] / 200000 * 1000

    assert abs(link["latency_ms"] - expected_latency) < 0.000001


def test_quality_is_calculated_correctly(client: TestClient) -> None:
    """Quality reflects the target 100 km terminal spacing rule."""

    headers = auth_headers_for_role(client, "engineer")
    source = create_terminal(client, headers, name="Source Terminal")
    redundant = create_terminal(
        client,
        headers,
        name="Redundant Terminal",
        longitude=0.4,
    )
    acceptable = create_terminal(
        client,
        headers,
        name="Acceptable Terminal",
        longitude=0.6,
    )
    optimal = create_terminal(
        client,
        headers,
        name="Optimal Terminal",
        longitude=0.9,
    )
    suboptimal = create_terminal(
        client,
        headers,
        name="Suboptimal Terminal",
        longitude=2.0,
    )

    quality_by_target = {
        redundant["id"]: "redundant",
        acceptable["id"]: "acceptable",
        optimal["id"]: "optimal",
        suboptimal["id"]: "suboptimal",
    }
    for target_id, expected_quality in quality_by_target.items():
        link = create_link(client, headers, source["id"], target_id)
        assert link["quality"] == expected_quality


def test_inactive_link_can_be_updated(client: TestClient) -> None:
    """A link can be marked inactive after creation."""

    headers = auth_headers_for_role(client, "engineer")
    source, target = create_terminal_pair(client, headers, target_longitude=0.9)
    link = create_link(client, headers, source["id"], target["id"])

    response = client.patch(
        f"/api/v1/fiber-links/{link['id']}",
        json={"is_active": False},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_list_filters_and_map_endpoint(client: TestClient) -> None:
    """Fiber links can be filtered and returned in map-ready format."""

    engineer_headers = auth_headers_for_role(client, "engineer")
    register_user(client, "operator@example.com")
    operator_headers = login_headers(client, "operator@example.com")
    source, target = create_terminal_pair(
        client,
        engineer_headers,
        target_longitude=0.9,
    )
    link = create_link(
        client,
        engineer_headers,
        source["id"],
        target["id"],
        is_active=False,
    )

    list_response = client.get(
        "/api/v1/fiber-links",
        params={"is_active": False, "quality": "optimal", "terminal_id": source["id"]},
        headers=operator_headers,
    )
    map_response = client.get("/api/v1/fiber-links/map", headers=operator_headers)

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [link["id"]]
    assert map_response.status_code == 200
    assert map_response.json()[0]["source_name"] == "Source Terminal"
    assert map_response.json()[0]["target_latitude"] == 0


def test_deleting_link_works(client: TestClient) -> None:
    """Engineer users can delete fiber links."""

    headers = auth_headers_for_role(client, "engineer")
    source, target = create_terminal_pair(client, headers, target_longitude=0.9)
    link = create_link(client, headers, source["id"], target["id"])

    delete_response = client.delete(
        f"/api/v1/fiber-links/{link['id']}",
        headers=headers,
    )
    get_response = client.get(f"/api/v1/fiber-links/{link['id']}", headers=headers)

    assert delete_response.status_code == 204
    assert get_response.status_code == 404
