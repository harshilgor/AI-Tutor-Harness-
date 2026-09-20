"""Durable lifecycle records for shared Ask/Learn generations."""
import sqlalchemy as sa
from alembic import op

revision = "0012_streaming_generations"
down_revision = "0011_assessment_quality"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "generation_records",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("owner_id", sa.String(160), nullable=False),
        sa.Column("session_id", sa.String(160), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("provider", sa.String(200), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cancellation_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("result", sa.Text()),
        sa.Column("error_code", sa.String(64)),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.UniqueConstraint("owner_id", "idempotency_key"),
    )
    op.create_index("ix_generation_owner_session", "generation_records", ["owner_id", "session_id", "status"])


def downgrade():
    op.drop_index("ix_generation_owner_session", table_name="generation_records")
    op.drop_table("generation_records")
