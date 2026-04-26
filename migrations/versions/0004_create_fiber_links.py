"""create fiber links.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create fiber links table."""

    op.create_table(
        "fiber_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_terminal_id", sa.Integer(), nullable=False),
        sa.Column("target_terminal_id", sa.Integer(), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("capacity_gbps", sa.Float(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "quality",
            sa.Enum(
                "optimal",
                "acceptable",
                "redundant",
                "suboptimal",
                name="fiber_link_quality",
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_terminal_id"],
            ["terminals.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_terminal_id"],
            ["terminals.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fiber_links_id"), "fiber_links", ["id"], unique=False)
    op.create_index(
        op.f("ix_fiber_links_source_terminal_id"),
        "fiber_links",
        ["source_terminal_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fiber_links_target_terminal_id"),
        "fiber_links",
        ["target_terminal_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop fiber links table."""

    op.drop_index(op.f("ix_fiber_links_target_terminal_id"), table_name="fiber_links")
    op.drop_index(op.f("ix_fiber_links_source_terminal_id"), table_name="fiber_links")
    op.drop_index(op.f("ix_fiber_links_id"), table_name="fiber_links")
    op.drop_table("fiber_links")
    sa.Enum(
        "optimal",
        "acceptable",
        "redundant",
        "suboptimal",
        name="fiber_link_quality",
    ).drop(op.get_bind(), checkfirst=True)
