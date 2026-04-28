"""create weather snapshots.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create weather snapshots table."""

    op.create_table(
        "weather_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("terminal_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cloud_cover_percent", sa.Float(), nullable=False),
        sa.Column("visibility_m", sa.Float(), nullable=True),
        sa.Column("precipitation_mm", sa.Float(), nullable=False),
        sa.Column("wind_speed_kmh", sa.Float(), nullable=False),
        sa.Column("wind_gusts_kmh", sa.Float(), nullable=False),
        sa.Column("temperature_c", sa.Float(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["terminal_id"],
            ["terminals.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_weather_snapshots_id"),
        "weather_snapshots",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_weather_snapshots_terminal_id"),
        "weather_snapshots",
        ["terminal_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop weather snapshots table."""

    op.drop_index(
        op.f("ix_weather_snapshots_terminal_id"),
        table_name="weather_snapshots",
    )
    op.drop_index(op.f("ix_weather_snapshots_id"), table_name="weather_snapshots")
    op.drop_table("weather_snapshots")
