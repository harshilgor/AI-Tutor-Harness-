"""Section-level provenance for tutor-maintained study notes.

The Markdown body stays clean: ownership, session linkage, and tombstones live
in this sidecar table, keyed by stable section IDs.
"""

import sqlalchemy as sa
from alembic import op

revision = "0013_note_section_provenance"
down_revision = "0012_streaming_generations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "note_section_provenance",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("owner_id", sa.String(160), nullable=False),
        sa.Column("note_id", sa.String(160), nullable=False),
        sa.Column("section_id", sa.String(160), nullable=False),
        sa.Column("heading", sa.String(300), nullable=False),
        sa.Column("owner_kind", sa.String(16), nullable=False),
        sa.Column("created_from", sa.String(200), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("concept_title", sa.String(300)),
        sa.Column("graph_concept_id", sa.String(160)),
        sa.Column("learner_concept_id", sa.String(160)),
        sa.Column("tombstoned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "note_id", "section_id", name="uq_section_owner_note_section"),
    )
    op.create_index("ix_section_provenance_note", "note_section_provenance", ["owner_id", "note_id"])


def downgrade() -> None:
    op.drop_index("ix_section_provenance_note", table_name="note_section_provenance")
    op.drop_table("note_section_provenance")
