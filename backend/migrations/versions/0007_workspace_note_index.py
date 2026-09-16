"""Add reconstructable metadata and search index for local Markdown notes."""

import sqlalchemy as sa
from alembic import op


revision = "0007_workspace_note_index"
down_revision = "0006_learning_workflows"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "workspace_notes",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("learner_id", sa.String(160), nullable=False),
        sa.Column("relative_path", sa.String(600), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("frontmatter_json", sa.Text(), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("learner_id", "relative_path", name="uq_workspace_note_owner_path"),
    )
    op.create_index("ix_workspace_notes_owner_updated", "workspace_notes", ["learner_id", "updated_at"])


def downgrade():
    op.drop_index("ix_workspace_notes_owner_updated", table_name="workspace_notes")
    op.drop_table("workspace_notes")
