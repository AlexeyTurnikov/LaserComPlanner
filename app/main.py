"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.config import get_settings
from app.users.router import router as users_router

settings = get_settings()

app = FastAPI(title=settings.project_name, version="0.1.0")
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(users_router, prefix=settings.api_v1_prefix)


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
