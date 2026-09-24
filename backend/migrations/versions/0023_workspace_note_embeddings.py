"""Cache embeddings for learner-owned workspace notes."""
import sqlalchemy as sa
from alembic import op

revision = "0023_workspace_note_embeddings"
down_revision = "0022_material_embeddings"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "workspace_note_embeddings",
        sa.Column("note_id", sa.String(160), sa.ForeignKey("workspace_notes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("model", sa.String(160), primary_key=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("vector_json", sa.Text(), nullable=False),
    )


def downgrade():
    op.drop_table("workspace_note_embeddings")
