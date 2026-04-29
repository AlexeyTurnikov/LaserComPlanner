"""Communication session API tests."""

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


def session_payload(terminal_id: int, **overrides: object) -> dict[str, object]:
    """Return a valid communication session payload."""

    payload: dict[str, object] = {
        "terminal_id": terminal_id,
        "start_time": "2026-04-28T10:00:00",
        "end_time": "2026-04-28T11:00:00",
        "status": "scheduled",
        "data_volume_gb": 50,
    }
    payload.update(overrides)
    return payload


def test_create_session(client: TestClient) -> None:
    """Engineer users can create communication sessions."""

    headers = auth_headers_for_role(client, "engineer")
    terminal = create_terminal(client, headers)

    response = client.post(
        "/api/v1/sessions",
        json=session_payload(terminal["id"]),
        headers=headers,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["terminal_id"] == terminal["id"]
    assert payload["status"] == "scheduled"
    assert payload["data_volume_gb"] == 50


def test_invalid_end_time_returns_422(client: TestClient) -> None:
    """end_time must be after start_time."""

    headers = auth_headers_for_role(client, "engineer")
    terminal = create_terminal(client, headers)

    response = client.post(
        "/api/v1/sessions",
        json=session_payload(
            terminal["id"],
            start_time="2026-04-28T11:00:00",
            end_time="2026-04-28T10:00:00",
        ),
        headers=headers,
    )

    assert response.status_code == 422


def test_overlapping_session_returns_400(client: TestClient) -> None:
    """Scheduled or active sessions cannot overlap for one terminal."""

    headers = auth_headers_for_role(client, "engineer")
    terminal = create_terminal(client, headers)
    create_response = client.post(
        "/api/v1/sessions",
        json=session_payload(terminal["id"]),
        headers=headers,
    )
    assert create_response.status_code == 201

    response = client.post(
        "/api/v1/sessions",
        json=session_payload(
            terminal["id"],
            start_time="2026-04-28T10:30:00",
            end_time="2026-04-28T11:30:00",
        ),
        headers=headers,
    )

    assert response.status_code == 400
    assert "overlaps" in response.json()["detail"]


def test_non_overlapping_session_allowed(client: TestClient) -> None:
    """Non-overlapping sessions are allowed for the same terminal."""

    headers = auth_headers_for_role(client, "engineer")
    terminal = create_terminal(client, headers)
    first_response = client.post(
        "/api/v1/sessions",
        json=session_payload(terminal["id"]),
        headers=headers,
    )
    second_response = client.post(
        "/api/v1/sessions",
        json=session_payload(
            terminal["id"],
            start_time="2026-04-28T11:00:00",
            end_time="2026-04-28T12:00:00",
        ),
        headers=headers,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201


def test_operator_cannot_create_session(client: TestClient) -> None:
    """Operator users cannot create communication sessions."""

    admin_headers = auth_headers_for_role(client, "admin")
    register_user(client, "operator@example.com")
    operator_headers = login_headers(client, "operator@example.com")
    terminal = create_terminal(client, admin_headers)

    response = client.post(
        "/api/v1/sessions",
        json=session_payload(terminal["id"]),
        headers=operator_headers,
    )

    assert response.status_code == 403


def test_update_and_delete_session(client: TestClient) -> None:
    """Engineer users can update and delete communication sessions."""

    headers = auth_headers_for_role(client, "engineer")
    terminal = create_terminal(client, headers)
    create_response = client.post(
        "/api/v1/sessions",
        json=session_payload(terminal["id"]),
        headers=headers,
    )
    session_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/sessions/{session_id}",
        json={"status": "completed"},
        headers=headers,
    )
    delete_response = client.delete(f"/api/v1/sessions/{session_id}", headers=headers)
    get_response = client.get(f"/api/v1/sessions/{session_id}", headers=headers)

    assert update_response.status_code == 200
    assert update_response.json()["status"] == "completed"
    assert delete_response.status_code == 204
    assert get_response.status_code == 404
