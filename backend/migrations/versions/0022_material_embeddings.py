"""Cache provider embeddings for owned material blocks."""
import sqlalchemy as sa
from alembic import op

revision = "0022_material_embeddings"
down_revision = "0021_one_active_generation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "material_embeddings",
        sa.Column("block_id", sa.String(160), sa.ForeignKey("material_blocks.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("model", sa.String(160), primary_key=True),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("vector_json", sa.Text(), nullable=False),
    )


def downgrade():
    op.drop_table("material_embeddings")
