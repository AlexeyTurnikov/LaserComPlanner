"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.availability.router import map_router as availability_map_router
from app.availability.router import router as availability_router
from app.auth.router import router as auth_router
from app.config import get_settings
from app.fiber_links.router import router as fiber_links_router
from app.terminals.router import router as terminals_router
from app.users.router import router as users_router
from app.weather.router import router as weather_router

settings = get_settings()

app = FastAPI(title=settings.project_name, version="0.1.0")
app.include_router(availability_router, prefix=settings.api_v1_prefix)
app.include_router(availability_map_router, prefix=settings.api_v1_prefix)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(fiber_links_router, prefix=settings.api_v1_prefix)
app.include_router(terminals_router, prefix=settings.api_v1_prefix)
app.include_router(users_router, prefix=settings.api_v1_prefix)
app.include_router(weather_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Return service health status."""

    return {"status": "ok"}


@app.get(f"{settings.api_v1_prefix}/info", tags=["system"])
def project_info() -> dict[str, str]:
    """Return basic project information."""

    return {
        "project_name": settings.project_name,
        "version": "0.1.0",
        "description": (
            "FastAPI service for planning laser ground terminal availability "
            "and data transmission routes."
        ),
    }
