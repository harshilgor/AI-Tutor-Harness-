"""Add the minimal lifecycle needed for authoritative adaptive recommendations."""

import sqlalchemy as sa
from alembic import op

revision = "0017_recommendation_lifecycle"
down_revision = "0016_web_evidence_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("recommendation_sets")}
    additions = (
        ("status", sa.String(24)),
        ("input_digest", sa.String(64)),
        ("superseded_by_set_id", sa.String(160)),
        ("fulfilled_evidence_id", sa.String(160)),
    )
    for name, column_type in additions:
        if name not in columns:
            op.add_column("recommendation_sets", sa.Column(name, column_type, nullable=True))

    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE recommendation_sets
        SET status='superseded', input_digest=context_key
        WHERE status IS NULL
    """))
    connection.execute(sa.text("""
        UPDATE recommendation_sets
        SET status='current'
        WHERE NOT EXISTS (
            SELECT 1 FROM recommendation_sets latest
            WHERE latest.owner_id=recommendation_sets.owner_id
              AND latest.session_id=recommendation_sets.session_id
              AND (
                latest.created_at > recommendation_sets.created_at
                OR (
                    latest.created_at = recommendation_sets.created_at
                    AND latest.id > recommendation_sets.id
                )
            )
        )
    """))
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("recommendation_sets")}
    if "ix_recommendation_sets_current" not in indexes:
        op.create_index(
            "ix_recommendation_sets_current",
            "recommendation_sets",
            ["owner_id", "session_id", "status"],
        )


def downgrade() -> None:
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("recommendation_sets")}
    if "ix_recommendation_sets_current" in indexes:
        op.drop_index("ix_recommendation_sets_current", table_name="recommendation_sets")
    for column in ("fulfilled_evidence_id", "superseded_by_set_id", "input_digest", "status"):
        op.drop_column("recommendation_sets", column)
