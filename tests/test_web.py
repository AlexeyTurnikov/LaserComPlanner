"""Server-rendered web page tests."""

from fastapi.testclient import TestClient


def test_root_redirects_to_dashboard(client: TestClient) -> None:
    """Root page redirects to dashboard."""

    response = client.get("/", follow_redirects=False)

    assert response.status_code in {302, 307}
    assert response.headers["location"] == "/dashboard"


def test_login_page_renders(client: TestClient) -> None:
    """Login page renders the auth form."""

    response = client.get("/login")

    assert response.status_code == 200
    assert "LaserGround Planner" in response.text
    assert "login-form" in response.text


def test_dashboard_page_renders(client: TestClient) -> None:
    """Dashboard page renders the Leaflet map container."""

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "dashboard-map" in response.text
    assert "/static/js/map.js" in response.text


def test_planner_page_renders(client: TestClient) -> None:
    """Planner page renders the form and map container."""

    response = client.get("/planner")

    assert response.status_code == 200
    assert "planner-form" in response.text
    assert "planner-map" in response.text


def test_terminal_detail_page_renders(client: TestClient) -> None:
    """Terminal detail page embeds terminal ID for client-side loading."""

    response = client.get("/terminals/42/view")

    assert response.status_code == 200
    assert 'data-terminal-id="42"' in response.text
    assert "/static/js/terminal_detail.js" in response.text


def test_static_assets_are_served(client: TestClient) -> None:
    """Static CSS and JS files are available."""

    css_response = client.get("/static/css/styles.css")
    js_response = client.get("/static/js/map.js")

    assert css_response.status_code == 200
    assert js_response.status_code == 200
