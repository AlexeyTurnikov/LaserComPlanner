"""create terminals.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create terminals table."""

    op.create_table(
        "terminals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("altitude_m", sa.Float(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "online",
                "offline",
                "maintenance",
                name="terminal_status",
            ),
            server_default="online",
            nullable=False,
        ),
        sa.Column("max_data_rate_gbps", sa.Float(), nullable=False),
        sa.Column("min_elevation_deg", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_terminals_id"), "terminals", ["id"], unique=False)
    op.create_index(op.f("ix_terminals_name"), "terminals", ["name"], unique=False)


def downgrade() -> None:
    """Drop terminals table."""

    op.drop_index(op.f("ix_terminals_name"), table_name="terminals")
    op.drop_index(op.f("ix_terminals_id"), table_name="terminals")
    op.drop_table("terminals")
    sa.Enum(
        "online",
        "offline",
        "maintenance",
        name="terminal_status",
    ).drop(op.get_bind(), checkfirst=True)
