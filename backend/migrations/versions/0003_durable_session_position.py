"""Expose durable session ownership and position alongside legacy payloads."""

import json
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "0003_durable_session_position"
down_revision = "0002_persistent_learner_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("learning_sessions")}
    additions = (
        ("learner_id", sa.String(120)),
        ("current_concept_id", sa.String(160)),
        ("current_lesson_id", sa.String(160)),
        ("state_version", sa.Integer()),
        ("updated_at", sa.DateTime(timezone=True)),
    )
    for name, column_type in additions:
        if name not in columns:
            op.add_column("learning_sessions", sa.Column(name, column_type, nullable=True))

    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, payload FROM learning_sessions")).mappings().all()
    for row in rows:
        payload = json.loads(row["payload"])
        updated_at = payload.get("updatedAt", payload.get("updated_at"))
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        connection.execute(sa.text("""
            UPDATE learning_sessions SET learner_id=:learner_id, current_concept_id=:current_concept_id,
            current_lesson_id=:current_lesson_id, state_version=:state_version, updated_at=:updated_at WHERE id=:id
        """), {
            "id": row["id"],
            "learner_id": payload.get("learnerId", payload.get("learner_id", "local")),
            "current_concept_id": payload.get("currentConceptId", payload.get("current_concept_id")),
            "current_lesson_id": payload.get("currentLessonId", payload.get("current_lesson_id")),
            "state_version": payload.get("stateVersion", payload.get("state_version", 1)),
            "updated_at": updated_at,
        })
    op.create_index("ix_learning_sessions_learner", "learning_sessions", ["learner_id"])


def downgrade() -> None:
    op.drop_index("ix_learning_sessions_learner", table_name="learning_sessions")
    for column in ("updated_at", "state_version", "current_lesson_id", "current_concept_id", "learner_id"):
        op.drop_column("learning_sessions", column)
