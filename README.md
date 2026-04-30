# LaserGround Planner

LaserGround Planner is a FastAPI training project for monitoring laser ground terminals and planning a data transmission route to a terminal that is currently available for satellite communication. The system combines terminal status, weather snapshots, availability scoring, fiber link quality, and shortest-path routing.

## Problem

Laser ground terminals are sensitive to cloud cover, precipitation, visibility, wind, hardware status, and schedule conflicts. If the local terminal cannot communicate with a satellite, data can be sent through the terrestrial fiber network to another available terminal.

## Features

- JWT authorization with `admin`, `engineer`, and `operator` roles.
- User management and role-based dependencies.
- CRUD for ground terminals.
- CRUD for fiber links with Haversine distance, latency, and 100 km quality rule.
- Open-Meteo integration for weather snapshots.
- Availability scoring with explainable reasons.
- Transmission requests and scheduled communication sessions.
- Dijkstra routing over active fiber links.
- Transmission planner that selects the best available terminal.
- Jinja2 + Leaflet dashboard and planner UI.
- Pytest + FastAPI TestClient coverage for core business logic.

## Stack

- Python 3.11+
- FastAPI, Uvicorn
- SQLAlchemy 2.x, Alembic
- PostgreSQL
- Pydantic v2, pydantic-settings
- python-jose, passlib bcrypt
- httpx
- Jinja2, Leaflet.js
- pytest, pytest-cov, pylint
- Docker, Docker Compose

## Architecture

The project is split by domain modules under `app/`: `auth`, `users`, `terminals`, `fiber_links`, `weather`, `availability`, `transmission_requests`, `sessions`, `routing`, and `web`. API routers stay thin, while persistence and business rules live in `service.py`, and routing logic lives in `app/routing/algorithms.py`.

## Database

Main tables:

- `users`
- `terminals`
- `fiber_links`
- `weather_snapshots`
- `availability_checks`
- `transmission_requests`
- `routing_results`
- `sessions`

## Main Endpoints

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/users/me`
- `GET /api/v1/terminals`
- `POST /api/v1/terminals`
- `GET /api/v1/fiber-links`
- `POST /api/v1/weather/update/{terminal_id}`
- `POST /api/v1/availability/check-all`
- `GET /api/v1/availability-map`
- `POST /api/v1/transmission-requests`
- `POST /api/v1/routing/transmission-plan`
- `GET /dashboard`
- `GET /planner`

## Run

```bash
git clone git@github.com:AlexeyTurnikov/LaserComPlanner.git
cd LaserComPlanner
cp .env.example .env
docker compose up --build
```

In another terminal:

```bash
docker compose exec app alembic upgrade head
docker compose exec app python scripts/seed_demo_data.py
```

Open:

- API docs: `http://localhost:8000/docs`
- Healthcheck: `http://localhost:8000/health`
- Dashboard: `http://localhost:8000/dashboard`
- Planner: `http://localhost:8000/planner`

## Local Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Tests

```bash
pytest
pytest --cov=app
pytest --cov=app --cov-report=term-missing
```

The tests mock Open-Meteo and do not perform real external weather requests.

## Pylint

```bash
pylint app > pylint.txt
```

The latest report is stored in `pylint.txt`.

## Demo Scenario

1. Start the app and apply migrations.
2. Run `python scripts/seed_demo_data.py`.
3. Log in as `operator@laserground.dev` with password `operator123`.
4. Open `/dashboard` and inspect terminal availability on the Leaflet map.
5. Open `/planner`, choose `Moscow Terminal`, and request a high-priority transfer.
6. Review the recommended available terminal, fiber route, score, and decision reasons.

## Demo Users

- `admin@laserground.dev` / `admin123`
- `engineer@laserground.dev` / `engineer123`
- `operator@laserground.dev` / `operator123`

## Author

Alexey Turnikov.
