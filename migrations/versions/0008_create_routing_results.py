"""create routing results.

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create routing results table."""

    op.create_table(
        "routing_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("selected_terminal_id", sa.Integer(), nullable=False),
        sa.Column("route_terminal_ids", sa.JSON(), nullable=False),
        sa.Column("route_distance_km", sa.Float(), nullable=False),
        sa.Column("estimated_latency_ms", sa.Float(), nullable=False),
        sa.Column("estimated_transfer_time_sec", sa.Float(), nullable=False),
        sa.Column("final_score", sa.Float(), nullable=False),
        sa.Column("decision_reason", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["transmission_requests.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["selected_terminal_id"],
            ["terminals.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_routing_results_id"), "routing_results", ["id"], unique=False)
    op.create_index(
        op.f("ix_routing_results_request_id"),
        "routing_results",
        ["request_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_routing_results_selected_terminal_id"),
        "routing_results",
        ["selected_terminal_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop routing results table."""

    op.drop_index(
        op.f("ix_routing_results_selected_terminal_id"),
        table_name="routing_results",
    )
    op.drop_index(op.f("ix_routing_results_request_id"), table_name="routing_results")
    op.drop_index(op.f("ix_routing_results_id"), table_name="routing_results")
    op.drop_table("routing_results")
