"""create availability checks.

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create availability checks table."""

    op.create_table(
        "availability_checks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("terminal_id", sa.Integer(), nullable=False),
        sa.Column("weather_snapshot_id", sa.Integer(), nullable=False),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("availability_score", sa.Float(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "available",
                "limited",
                "unavailable",
                name="availability_status",
            ),
            nullable=False,
        ),
        sa.Column("reason", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["terminal_id"],
            ["terminals.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["weather_snapshot_id"],
            ["weather_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_availability_checks_created_by_user_id"),
        "availability_checks",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_availability_checks_id"),
        "availability_checks",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_availability_checks_terminal_id"),
        "availability_checks",
        ["terminal_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_availability_checks_weather_snapshot_id"),
        "availability_checks",
        ["weather_snapshot_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop availability checks table."""

    op.drop_index(
        op.f("ix_availability_checks_weather_snapshot_id"),
        table_name="availability_checks",
    )
    op.drop_index(
        op.f("ix_availability_checks_terminal_id"),
        table_name="availability_checks",
    )
    op.drop_index(op.f("ix_availability_checks_id"), table_name="availability_checks")
    op.drop_index(
        op.f("ix_availability_checks_created_by_user_id"),
        table_name="availability_checks",
    )
    op.drop_table("availability_checks")
    sa.Enum(
        "available",
        "limited",
        "unavailable",
        name="availability_status",
    ).drop(op.get_bind(), checkfirst=True)
