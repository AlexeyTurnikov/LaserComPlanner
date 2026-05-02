"""Alembic environment configuration."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.availability import models as availability_models
from app.base import Base
from app.config import get_settings
from app.fiber_links import models as fiber_links_models
from app.routing import models as routing_models
from app.sessions import models as sessions_models
from app.terminals import models as terminals_models
from app.transmission_requests import models as transmission_requests_models
from app.users import models as users_models
from app.weather import models as weather_models

MODEL_MODULES = (
    availability_models,
    fiber_links_models,
    routing_models,
    sessions_models,
    terminals_models,
    transmission_requests_models,
    users_models,
    weather_models,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """Return database URL from application settings."""

    return get_settings().database_url


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""

    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with an active database connection."""

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
