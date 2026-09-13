"""Record the existing graph and teaching persistence baseline."""

import sqlalchemy as sa
from alembic import op

revision = "0001_legacy_baseline"
down_revision = None
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    definitions = (
        ("topic_scopes", [sa.Column("id", sa.String(160), primary_key=True), sa.Column("payload", sa.Text(), nullable=False)]),
        ("graph_jobs", [sa.Column("id", sa.String(160), primary_key=True), sa.Column("scope_id", sa.String(160), sa.ForeignKey("topic_scopes.id"), nullable=False), sa.Column("payload", sa.Text(), nullable=False)]),
        ("graph_versions", [sa.Column("id", sa.String(160), primary_key=True), sa.Column("scope_id", sa.String(160), sa.ForeignKey("topic_scopes.id"), nullable=False), sa.Column("payload", sa.Text(), nullable=False)]),
        ("learning_sessions", [sa.Column("id", sa.String(160), primary_key=True), sa.Column("graph_id", sa.String(160), sa.ForeignKey("graph_versions.id"), nullable=False), sa.Column("payload", sa.Text(), nullable=False)]),
        ("learning_actions", [sa.Column("id", sa.String(160), primary_key=True), sa.Column("session_id", sa.String(160), sa.ForeignKey("learning_sessions.id"), nullable=False), sa.Column("idempotency_key", sa.String(200)), sa.Column("payload", sa.Text(), nullable=False)]),
        ("lesson_artifacts", [sa.Column("id", sa.String(160), primary_key=True), sa.Column("session_id", sa.String(160), sa.ForeignKey("learning_sessions.id"), nullable=False), sa.Column("payload", sa.Text(), nullable=False)]),
        ("action_events", [sa.Column("id", sa.String(160), primary_key=True), sa.Column("action_id", sa.String(160), sa.ForeignKey("learning_actions.id"), nullable=False), sa.Column("sequence", sa.Integer(), nullable=False), sa.Column("payload", sa.Text(), nullable=False)]),
        ("learner_graphs", [sa.Column("learner_id", sa.String(120), primary_key=True), sa.Column("payload", sa.Text(), nullable=False)]),
        ("learner_graph_concepts", [sa.Column("learner_id", sa.String(120), primary_key=True), sa.Column("id", sa.String(160), primary_key=True), sa.Column("canonical_key", sa.String(400), nullable=False), sa.Column("payload", sa.Text(), nullable=False)]),
        ("learner_graph_edges", [sa.Column("learner_id", sa.String(120), primary_key=True), sa.Column("id", sa.String(160), primary_key=True), sa.Column("source_concept_id", sa.String(160), nullable=False), sa.Column("target_concept_id", sa.String(160), nullable=False), sa.Column("edge_type", sa.String(60), nullable=False), sa.Column("payload", sa.Text(), nullable=False)]),
        ("learner_graph_events", [sa.Column("id", sa.String(160), primary_key=True), sa.Column("learner_id", sa.String(120), nullable=False), sa.Column("concept_id", sa.String(160), nullable=False), sa.Column("event_type", sa.String(80), nullable=False), sa.Column("payload", sa.Text(), nullable=False), sa.Column("created_at", sa.String(50), nullable=False, server_default="")]),
    )
    for name, columns in definitions:
        if not _has_table(name):
            op.create_table(name, *columns)
    event_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("learner_graph_events")}
    if "created_at" not in event_columns:
        op.add_column("learner_graph_events", sa.Column("created_at", sa.String(50), nullable=False, server_default=""))
    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("learning_actions")}
    if "uq_learning_action_idempotency" not in indexes:
        op.create_index("uq_learning_action_idempotency", "learning_actions", ["session_id", "idempotency_key"], unique=True)
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("action_events")}
    if "uq_action_event_sequence" not in indexes:
        op.create_index("uq_action_event_sequence", "action_events", ["action_id", "sequence"], unique=True)


def downgrade() -> None:
    pass  # Baseline downgrade never destroys legacy user data.
