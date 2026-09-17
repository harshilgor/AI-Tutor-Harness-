"""Persist item exposure counts independently of private assessment artifacts."""
import sqlalchemy as sa
from alembic import op

revision = "0011_assessment_quality"
down_revision = "0010_state_projection_challenges"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assessment_item_exposure",
        sa.Column("owner_id", sa.String(160), nullable=False),
        sa.Column("fingerprint", sa.String(512), nullable=False),
        sa.Column("item_id", sa.String(160), nullable=False),
        sa.Column("presented_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_presented_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("owner_id", "fingerprint"),
    )
    op.create_index("ix_assessment_exposure_item", "assessment_item_exposure", ["owner_id", "item_id"])


def downgrade():
    op.drop_index("ix_assessment_exposure_item", table_name="assessment_item_exposure")
    op.drop_table("assessment_item_exposure")
