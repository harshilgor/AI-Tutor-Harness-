"""Persist generation stream events for reconnects and process restarts."""
import sqlalchemy as sa
from alembic import op

revision = "0024_generation_event_replay"
down_revision = "0023_workspace_note_embeddings"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "generation_events",
        sa.Column("generation_id", sa.String(80), sa.ForeignKey("generation_records.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("sequence", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("data_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
    )


def downgrade():
    op.drop_table("generation_events")
