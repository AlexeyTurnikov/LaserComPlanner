"""create transmission requests and sessions.

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create transmission requests and sessions tables."""

    op.create_table(
        "transmission_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("source_terminal_id", sa.Integer(), nullable=False),
        sa.Column("data_volume_gb", sa.Float(), nullable=False),
        sa.Column(
            "priority",
            sa.Enum("low", "normal", "high", name="transmission_priority"),
            server_default="normal",
            nullable=False,
        ),
        sa.Column("min_availability_score", sa.Float(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "created",
                "planned",
                "failed",
                "completed",
                name="transmission_request_status",
            ),
            server_default="created",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_terminal_id"],
            ["terminals.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_transmission_requests_created_by_user_id"),
        "transmission_requests",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_transmission_requests_id"),
        "transmission_requests",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_transmission_requests_source_terminal_id"),
        "transmission_requests",
        ["source_terminal_id"],
        unique=False,
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("terminal_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "scheduled",
                "active",
                "completed",
                "cancelled",
                name="session_status",
            ),
            server_default="scheduled",
            nullable=False,
        ),
        sa.Column("data_volume_gb", sa.Float(), nullable=False),
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
    op.create_index(op.f("ix_sessions_id"), "sessions", ["id"], unique=False)
    op.create_index(
        op.f("ix_sessions_terminal_id"),
        "sessions",
        ["terminal_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop transmission requests and sessions tables."""

    op.drop_index(op.f("ix_sessions_terminal_id"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_id"), table_name="sessions")
    op.drop_table("sessions")
    sa.Enum(
        "scheduled",
        "active",
        "completed",
        "cancelled",
        name="session_status",
    ).drop(op.get_bind(), checkfirst=True)

    op.drop_index(
        op.f("ix_transmission_requests_source_terminal_id"),
        table_name="transmission_requests",
    )
    op.drop_index(
        op.f("ix_transmission_requests_id"),
        table_name="transmission_requests",
    )
    op.drop_index(
        op.f("ix_transmission_requests_created_by_user_id"),
        table_name="transmission_requests",
    )
    op.drop_table("transmission_requests")
    sa.Enum(
        "created",
        "planned",
        "failed",
        "completed",
        name="transmission_request_status",
    ).drop(op.get_bind(), checkfirst=True)
    sa.Enum("low", "normal", "high", name="transmission_priority").drop(
        op.get_bind(),
        checkfirst=True,
    )
