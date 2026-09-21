"""Concept memory states, relationships, and richer review schedules."""

import sqlalchemy as sa
from alembic import op

revision = "0014_review_memory"
down_revision = "0013_note_section_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "concept_memory_states",
        sa.Column("learner_id", sa.String(120), sa.ForeignKey("learners.id"), primary_key=True),
        sa.Column("concept_id", sa.String(160), primary_key=True),
        sa.Column("graph_id", sa.String(160), nullable=False),
        sa.Column("graph_version", sa.Integer(), nullable=False),
        sa.Column("first_learned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_recall_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_recall_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("partial_recall_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skip_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consecutive_successes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("difficulty_estimate", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("last_score", sa.Float()),
        sa.Column("last_confidence", sa.String(40)),
        sa.Column("last_outcome", sa.String(40)),
        sa.Column("last_question_type", sa.String(40)),
        sa.Column("mastery_estimate", sa.String(40), nullable=False, server_default="recently_learned"),
        sa.Column("needs_remediation", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source_lesson_id", sa.String(160)),
        sa.Column("source_session_id", sa.String(160)),
        sa.Column("source_section_id", sa.String(160)),
        sa.Column("provenance_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_concept_memory_next_review", "concept_memory_states", ["learner_id", "next_review_at"])
    op.create_index("ix_concept_memory_mastery", "concept_memory_states", ["learner_id", "mastery_estimate"])

    op.create_table(
        "concept_relationships",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("learner_id", sa.String(120), sa.ForeignKey("learners.id"), nullable=False),
        sa.Column("source_concept_id", sa.String(160), nullable=False),
        sa.Column("target_concept_id", sa.String(160), nullable=False),
        sa.Column("relationship_type", sa.String(40), nullable=False),
        sa.Column("provenance_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("learner_id", "source_concept_id", "target_concept_id", "relationship_type", name="uq_concept_relationship"),
    )
    op.create_index("ix_concept_relationships_learner", "concept_relationships", ["learner_id", "source_concept_id"])

    op.create_table(
        "concept_sync_runs",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("learner_id", sa.String(120), sa.ForeignKey("learners.id"), nullable=False),
        sa.Column("source_key", sa.String(240), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("learner_id", "source_key", "content_hash", name="uq_concept_sync_run"),
    )

    with op.batch_alter_table("review_schedules") as batch:
        batch.add_column(sa.Column("due_reason", sa.String(120)))
        batch.add_column(sa.Column("activity_type", sa.String(40)))
        batch.add_column(sa.Column("confidence_at_schedule", sa.String(40)))
        batch.add_column(sa.Column("scheduler_version", sa.String(40)))
        batch.add_column(sa.Column("priority_score", sa.Float()))


def downgrade() -> None:
    with op.batch_alter_table("review_schedules") as batch:
        batch.drop_column("priority_score")
        batch.drop_column("scheduler_version")
        batch.drop_column("confidence_at_schedule")
        batch.drop_column("activity_type")
        batch.drop_column("due_reason")
    op.drop_table("concept_sync_runs")
    op.drop_table("concept_relationships")
    op.drop_table("concept_memory_states")
