"""Add server-authoritative session revision and activity pointers."""

import json

import sqlalchemy as sa
from alembic import op

revision = "0018_session_authority"
down_revision = "0017_recommendation_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("learning_sessions")}
    additions = (
        ("authority_revision", sa.Integer()),
        ("current_branch_id", sa.String(160)),
        ("active_generation_id", sa.String(160)),
        ("active_quiz_id", sa.String(160)),
        ("active_review_id", sa.String(160)),
        ("active_job_id", sa.String(160)),
    )
    for name, column_type in additions:
        if name not in columns:
            op.add_column("learning_sessions", sa.Column(name, column_type, nullable=True))

    connection = op.get_bind()
    rows = connection.execute(sa.text("""
        SELECT id,payload,state_version FROM learning_sessions
    """)).mappings().all()
    for row in rows:
        payload = json.loads(row["payload"])
        revision_value = int(row["state_version"] or payload.get("stateVersion") or 1)
        payload.setdefault("authorityRevision", revision_value)
        connection.execute(sa.text("""
            UPDATE learning_sessions
            SET authority_revision=:revision, payload=:payload
            WHERE id=:id
        """), {
            "id": row["id"],
            "revision": revision_value,
            "payload": json.dumps(payload, separators=(",", ":")),
        })


def downgrade() -> None:
    for column in (
        "active_job_id",
        "active_review_id",
        "active_quiz_id",
        "active_generation_id",
        "current_branch_id",
        "authority_revision",
    ):
        op.drop_column("learning_sessions", column)
