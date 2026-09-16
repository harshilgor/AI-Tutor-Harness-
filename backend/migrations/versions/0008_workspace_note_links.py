"""Add a rebuildable link and backlink index for workspace Markdown notes."""

import sqlalchemy as sa
from alembic import op


revision = "0008_workspace_note_links"
down_revision = "0007_workspace_note_index"
branch_labels = None
depends_on = None


def upgrade():
    # There are deliberately no foreign keys here. A deleted note target must
    # remain visible as a broken learner reference until the learner repairs or
    # removes it, and Markdown frontmatter can rebuild this table.
    op.create_table(
        "workspace_note_links",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("learner_id", sa.String(160), nullable=False),
        sa.Column("source_note_id", sa.String(160), nullable=False),
        sa.Column("target_type", sa.String(40), nullable=False),
        sa.Column("target_id", sa.String(360), nullable=False),
        sa.Column("label", sa.String(300)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("learner_id", "source_note_id", "target_type", "target_id", name="uq_workspace_note_link_target"),
    )
    op.create_index("ix_workspace_note_links_source", "workspace_note_links", ["learner_id", "source_note_id"])
    op.create_index("ix_workspace_note_links_target", "workspace_note_links", ["learner_id", "target_type", "target_id"])


def downgrade():
    op.drop_index("ix_workspace_note_links_target", table_name="workspace_note_links")
    op.drop_index("ix_workspace_note_links_source", table_name="workspace_note_links")
    op.drop_table("workspace_note_links")
