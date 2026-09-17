"""Persist deterministic next-action recommendations and display-safe interactions."""
import sqlalchemy as sa
from alembic import op

revision = "0009_next_action_recommendations"
down_revision = "0008_workspace_note_links"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "recommendation_sets",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("owner_id", sa.String(160), nullable=False),
        sa.Column("session_id", sa.String(160), nullable=False),
        sa.Column("context_key", sa.String(200), nullable=False),
        sa.Column("policy_version", sa.String(80), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "session_id", "context_key", "policy_version", name="uq_recommendation_set_context"),
    )
    op.create_index("ix_recommendation_sets_owner_session", "recommendation_sets", ["owner_id", "session_id", "created_at"])
    op.create_table(
        "next_action_recommendations",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("set_id", sa.String(160), sa.ForeignKey("recommendation_sets.id"), nullable=False),
        sa.Column("owner_id", sa.String(160), nullable=False),
        sa.Column("action_kind", sa.String(24), nullable=False),
        sa.Column("concept_id", sa.String(160)),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.UniqueConstraint("set_id", "rank", name="uq_recommendation_rank"),
    )
    op.create_index("ix_next_action_recommendations_set", "next_action_recommendations", ["set_id", "rank"])
    op.create_table(
        "recommendation_interactions",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("owner_id", sa.String(160), nullable=False),
        sa.Column("recommendation_id", sa.String(160), sa.ForeignKey("next_action_recommendations.id"), nullable=False),
        sa.Column("event_type", sa.String(24), nullable=False),
        sa.Column("idempotency_key", sa.String(200)),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "recommendation_id", "event_type", "idempotency_key", name="uq_recommendation_interaction_key"),
    )
    op.create_index("ix_recommendation_interactions_owner", "recommendation_interactions", ["owner_id", "recommendation_id", "created_at"])


def downgrade():
    op.drop_table("recommendation_interactions")
    op.drop_table("next_action_recommendations")
    op.drop_table("recommendation_sets")
