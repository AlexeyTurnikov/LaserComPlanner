"""Terminal CRUD API tests."""

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


def terminal_payload(**overrides: object) -> dict[str, object]:
    """Return a valid terminal payload with optional overrides."""

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
    """Create a terminal and return the response JSON."""

    response = client.post(
        "/api/v1/terminals",
        json=terminal_payload(**overrides),
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_create_terminal_as_admin(client: TestClient) -> None:
    """Admin users can create terminals."""

    headers = auth_headers_for_role(client, "admin")

    payload = create_terminal(client, headers)

    assert payload["name"] == "Moscow Terminal"
    assert payload["status"] == "online"
    assert payload["max_data_rate_gbps"] == 20


def test_create_terminal_as_engineer(client: TestClient) -> None:
    """Engineer users can create terminals."""

    headers = auth_headers_for_role(client, "engineer")

    payload = create_terminal(client, headers, name="Tula Terminal")

    assert payload["name"] == "Tula Terminal"


def test_operator_cannot_create_terminal(client: TestClient) -> None:
    """Operator users cannot create terminals."""

    headers = auth_headers_for_role(client, "operator")

    response = client.post(
        "/api/v1/terminals",
        json=terminal_payload(),
        headers=headers,
    )

    assert response.status_code == 403


def test_get_terminal_list(client: TestClient) -> None:
    """Authenticated users can list terminals with filters."""

    engineer_headers = auth_headers_for_role(client, "engineer")
    register_user(client, "operator@example.com")
    operator_headers = login_headers(client, "operator@example.com")
    create_terminal(client, engineer_headers, name="Moscow Terminal")
    create_terminal(
        client,
        engineer_headers,
        name="Tula Terminal",
        latitude=54.1961,
        longitude=37.6182,
        status="maintenance",
    )

    response = client.get(
        "/api/v1/terminals",
        params={"status": "maintenance", "search": "tula"},
        headers=operator_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["name"] == "Tula Terminal"


def test_get_terminal_by_id(client: TestClient) -> None:
    """Authenticated users can read one terminal."""

    engineer_headers = auth_headers_for_role(client, "engineer")
    register_user(client, "operator@example.com")
    operator_headers = login_headers(client, "operator@example.com")
    terminal = create_terminal(client, engineer_headers)

    response = client.get(
        f"/api/v1/terminals/{terminal['id']}",
        headers=operator_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == terminal["id"]


def test_update_terminal(client: TestClient) -> None:
    """Engineer users can update terminals."""

    headers = auth_headers_for_role(client, "engineer")
    terminal = create_terminal(client, headers)

    response = client.patch(
        f"/api/v1/terminals/{terminal['id']}",
        json={"status": "maintenance", "max_data_rate_gbps": 15},
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "maintenance"
    assert payload["max_data_rate_gbps"] == 15


def test_delete_terminal(client: TestClient) -> None:
    """Engineer users can delete terminals."""

    headers = auth_headers_for_role(client, "engineer")
    terminal = create_terminal(client, headers)

    delete_response = client.delete(
        f"/api/v1/terminals/{terminal['id']}",
        headers=headers,
    )
    get_response = client.get(
        f"/api/v1/terminals/{terminal['id']}",
        headers=headers,
    )

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_invalid_latitude_returns_422(client: TestClient) -> None:
    """Latitude must be in the valid geographic range."""

    headers = auth_headers_for_role(client, "engineer")

    response = client.post(
        "/api/v1/terminals",
        json=terminal_payload(latitude=120),
        headers=headers,
    )

    assert response.status_code == 422


def test_invalid_data_rate_returns_422(client: TestClient) -> None:
    """Maximum data rate must be positive."""

    headers = auth_headers_for_role(client, "engineer")

    response = client.post(
        "/api/v1/terminals",
        json=terminal_payload(max_data_rate_gbps=0),
        headers=headers,
    )

    assert response.status_code == 422
