"""Add canonical learner state, evidence, branches, notes, and review records."""

import sqlalchemy as sa
from alembic import op

revision = "0002_persistent_learner_state"
down_revision = "0001_legacy_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learners",
        sa.Column("id", sa.String(120), primary_key=True),
        sa.Column("identity_kind", sa.String(40), nullable=False),
        sa.Column("display_name", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "curriculum_scopes",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("owner_learner_id", sa.String(120), sa.ForeignKey("learners.id")),
        sa.Column("graph_id", sa.String(160), sa.ForeignKey("graph_versions.id"), nullable=False, unique=True),
        sa.Column("graph_version", sa.Integer(), nullable=False),
        sa.Column("compatibility_key", sa.String(220), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "learner_concept_states",
        sa.Column("learner_id", sa.String(120), sa.ForeignKey("learners.id"), primary_key=True),
        sa.Column("concept_id", sa.String(160), primary_key=True),
        sa.Column("graph_id", sa.String(160), sa.ForeignKey("graph_versions.id"), nullable=False),
        sa.Column("graph_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("uncertainty", sa.Float(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("last_evidence_id", sa.String(160)),
        sa.Column("policy_version", sa.String(80), nullable=False),
        sa.Column("provenance_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "state_events",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("learner_id", sa.String(120), sa.ForeignKey("learners.id"), nullable=False),
        sa.Column("kind", sa.String(100), nullable=False),
        sa.Column("concept_id", sa.String(160)),
        sa.Column("session_id", sa.String(160)),
        sa.Column("action_id", sa.String(160)),
        sa.Column("correlation_id", sa.String(160)),
        sa.Column("causation_id", sa.String(160)),
        sa.Column("idempotency_key", sa.String(200)),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("provenance_json", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("learner_id", "idempotency_key", name="uq_state_event_idempotency"),
    )
    op.create_index("ix_state_events_learner_time", "state_events", ["learner_id", "recorded_at"])
    op.create_table(
        "evidence",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("learner_id", sa.String(120), sa.ForeignKey("learners.id"), nullable=False),
        sa.Column("evidence_key", sa.String(200), nullable=False),
        sa.Column("concept_id", sa.String(160), nullable=False),
        sa.Column("graph_id", sa.String(160), sa.ForeignKey("graph_versions.id"), nullable=False),
        sa.Column("graph_version", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(80), nullable=False),
        sa.Column("outcome", sa.String(40), nullable=False),
        sa.Column("condition", sa.String(40), nullable=False),
        sa.Column("score", sa.Float()),
        sa.Column("evaluator", sa.String(160), nullable=False),
        sa.Column("reliability", sa.Float(), nullable=False),
        sa.Column("admission_status", sa.String(40), nullable=False),
        sa.Column("admission_reason", sa.String(300)),
        # Source events may live in either the legacy action log or the new
        # state-event log, so this heterogeneous provenance reference cannot
        # honestly use a single-table foreign key.
        sa.Column("source_event_id", sa.String(160)),
        sa.Column("supersedes_evidence_id", sa.String(160), sa.ForeignKey("evidence.id")),
        sa.Column("superseded_by_evidence_id", sa.String(160), sa.ForeignKey("evidence.id")),
        sa.Column("policy_version", sa.String(80), nullable=False),
        sa.Column("provenance_json", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("learner_id", "evidence_key", name="uq_evidence_key"),
    )
    op.create_index("ix_evidence_learner_concept", "evidence", ["learner_id", "concept_id", "created_at"])
    op.create_table(
        "misconception_hypotheses",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("learner_id", sa.String(120), sa.ForeignKey("learners.id"), nullable=False),
        sa.Column("concept_id", sa.String(160), nullable=False),
        sa.Column("code", sa.String(160), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("learner_id", "concept_id", "code", name="uq_misconception_hypothesis"),
    )
    op.create_table(
        "misconception_evidence_links",
        sa.Column("hypothesis_id", sa.String(160), sa.ForeignKey("misconception_hypotheses.id"), primary_key=True),
        sa.Column("evidence_id", sa.String(160), sa.ForeignKey("evidence.id"), primary_key=True),
        sa.Column("relationship", sa.String(40), nullable=False),
    )
    op.create_table(
        "review_schedules",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("learner_id", sa.String(120), sa.ForeignKey("learners.id"), nullable=False),
        sa.Column("concept_id", sa.String(160), nullable=False),
        sa.Column("originating_evidence_id", sa.String(160), sa.ForeignKey("evidence.id"), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("learner_id", "originating_evidence_id", name="uq_review_origin"),
    )
    op.create_index("ix_review_queue", "review_schedules", ["learner_id", "status", "due_at"])
    op.create_table(
        "review_history",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("schedule_id", sa.String(160), sa.ForeignKey("review_schedules.id"), nullable=False),
        sa.Column("learner_id", sa.String(120), sa.ForeignKey("learners.id"), nullable=False),
        sa.Column("evidence_id", sa.String(160), sa.ForeignKey("evidence.id"), nullable=False),
        sa.Column("outcome", sa.String(40), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "branches",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("learner_id", sa.String(120), sa.ForeignKey("learners.id"), nullable=False),
        sa.Column("session_id", sa.String(160), sa.ForeignKey("learning_sessions.id"), nullable=False),
        sa.Column("parent_branch_id", sa.String(160), sa.ForeignKey("branches.id")),
        sa.Column("anchor_json", sa.Text(), nullable=False),
        sa.Column("return_position_json", sa.Text(), nullable=False),
        sa.Column("lifecycle", sa.String(40), nullable=False),
        sa.Column("local_gear", sa.String(20)),
        sa.Column("summary", sa.Text()),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_branches_learner_session", "branches", ["learner_id", "session_id"])
    op.create_table(
        "notes",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("learner_id", sa.String(120), sa.ForeignKey("learners.id"), nullable=False),
        sa.Column("scope", sa.String(40), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("concept_id", sa.String(160)),
        sa.Column("lesson_id", sa.String(160)),
        sa.Column("branch_id", sa.String(160), sa.ForeignKey("branches.id")),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("provenance_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_notes_learner_updated", "notes", ["learner_id", "updated_at"])
    op.create_table(
        "note_revisions",
        sa.Column("note_id", sa.String(160), sa.ForeignKey("notes.id"), primary_key=True),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("provenance_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for table in (
        "note_revisions", "notes", "branches", "review_history", "review_schedules",
        "misconception_evidence_links", "misconception_hypotheses", "evidence",
        "state_events", "learner_concept_states", "curriculum_scopes", "learners",
    ):
        op.drop_table(table)
