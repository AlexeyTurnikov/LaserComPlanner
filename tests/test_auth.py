"""Authentication and user role API tests."""

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


def login_user(
    client: TestClient,
    email: str,
    password: str = "strongpass123",
) -> str:
    """Login and return an access token."""

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    return payload["access_token"]


def test_registration_works(client: TestClient) -> None:
    """First registered user is created as admin."""

    payload = register_user(client, "admin@example.com")

    assert payload["email"] == "admin@example.com"
    assert payload["role"] == "admin"
    assert payload["is_active"] is True
    assert "hashed_password" not in payload


def test_login_returns_token(client: TestClient) -> None:
    """Login returns a bearer JWT token."""

    register_user(client, "admin@example.com")

    token = login_user(client, "admin@example.com")

    assert isinstance(token, str)
    assert token.count(".") == 2


def test_users_me_without_token_returns_401(client: TestClient) -> None:
    """Current-user endpoint requires authentication."""

    response = client.get("/api/v1/users/me")

    assert response.status_code == 401


def test_users_me_with_token_returns_current_user(client: TestClient) -> None:
    """Current-user endpoint returns the authenticated user."""

    register_user(client, "admin@example.com")
    token = login_user(client, "admin@example.com")

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "admin@example.com"


def test_non_admin_cannot_list_users(client: TestClient) -> None:
    """Operator users cannot access the users list."""

    register_user(client, "admin@example.com")
    register_user(client, "operator@example.com")
    token = login_user(client, "operator@example.com")

    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_admin_can_list_users(client: TestClient) -> None:
    """Admin users can access the users list."""

    register_user(client, "admin@example.com")
    register_user(client, "operator@example.com")
    token = login_user(client, "admin@example.com")

    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert [user["email"] for user in response.json()] == [
        "admin@example.com",
        "operator@example.com",
    ]
