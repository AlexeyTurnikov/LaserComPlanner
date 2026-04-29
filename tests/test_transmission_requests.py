"""Transmission request API tests."""

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


def request_payload(source_terminal_id: int, **overrides: object) -> dict[str, object]:
    """Return a valid transmission request payload."""

    payload: dict[str, object] = {
        "source_terminal_id": source_terminal_id,
        "data_volume_gb": 120,
        "priority": "high",
        "min_availability_score": 0.75,
    }
    payload.update(overrides)
    return payload


def test_create_transmission_request(client: TestClient) -> None:
    """Operator users can create transmission requests."""

    admin_headers = auth_headers_for_role(client, "admin")
    register_user(client, "operator@example.com")
    operator_headers = login_headers(client, "operator@example.com")
    terminal = create_terminal(client, admin_headers)

    response = client.post(
        "/api/v1/transmission-requests",
        json=request_payload(terminal["id"]),
        headers=operator_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_terminal_id"] == terminal["id"]
    assert payload["data_volume_gb"] == 120
    assert payload["priority"] == "high"
    assert payload["status"] == "created"


def test_invalid_data_volume_returns_422(client: TestClient) -> None:
    """Transmission data volume must be positive."""

    admin_headers = auth_headers_for_role(client, "admin")
    register_user(client, "operator@example.com")
    operator_headers = login_headers(client, "operator@example.com")
    terminal = create_terminal(client, admin_headers)

    response = client.post(
        "/api/v1/transmission-requests",
        json=request_payload(terminal["id"], data_volume_gb=0),
        headers=operator_headers,
    )

    assert response.status_code == 422


def test_operator_sees_only_own_requests(client: TestClient) -> None:
    """Operators can list their own transmission requests only."""

    admin_headers = auth_headers_for_role(client, "admin")
    first_user = register_user(client, "operator@example.com")
    register_user(client, "other-operator@example.com")
    operator_headers = login_headers(client, "operator@example.com")
    other_headers = login_headers(client, "other-operator@example.com")
    terminal = create_terminal(client, admin_headers)

    own_response = client.post(
        "/api/v1/transmission-requests",
        json=request_payload(terminal["id"], data_volume_gb=100),
        headers=operator_headers,
    )
    other_response = client.post(
        "/api/v1/transmission-requests",
        json=request_payload(terminal["id"], data_volume_gb=200),
        headers=other_headers,
    )
    list_response = client.get(
        "/api/v1/transmission-requests",
        headers=operator_headers,
    )

    assert own_response.status_code == 200
    assert other_response.status_code == 200
    payload = list_response.json()
    assert list_response.status_code == 200
    assert len(payload) == 1
    assert payload[0]["created_by_user_id"] == first_user["id"]
    assert payload[0]["data_volume_gb"] == 100


def test_engineer_can_see_all_requests(client: TestClient) -> None:
    """Engineer users can list all transmission requests."""

    admin_headers = auth_headers_for_role(client, "admin")
    engineer_user = register_user(client, "engineer@example.com")
    register_user(client, "operator@example.com")
    role_response = client.patch(
        f"/api/v1/users/{engineer_user['id']}/role",
        json={"role": "engineer"},
        headers=admin_headers,
    )
    assert role_response.status_code == 200
    engineer_headers = login_headers(client, "engineer@example.com")
    operator_headers = login_headers(client, "operator@example.com")
    terminal = create_terminal(client, admin_headers)
    client.post(
        "/api/v1/transmission-requests",
        json=request_payload(terminal["id"], data_volume_gb=100),
        headers=operator_headers,
    )
    client.post(
        "/api/v1/transmission-requests",
        json=request_payload(terminal["id"], data_volume_gb=200),
        headers=admin_headers,
    )

    response = client.get(
        "/api/v1/transmission-requests",
        headers=engineer_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_update_transmission_request_status(client: TestClient) -> None:
    """Visible transmission request status can be updated."""

    admin_headers = auth_headers_for_role(client, "admin")
    register_user(client, "operator@example.com")
    operator_headers = login_headers(client, "operator@example.com")
    terminal = create_terminal(client, admin_headers)
    create_response = client.post(
        "/api/v1/transmission-requests",
        json=request_payload(terminal["id"]),
        headers=operator_headers,
    )
    request_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/transmission-requests/{request_id}/status",
        json={"status": "planned"},
        headers=operator_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "planned"
