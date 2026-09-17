"""Add audit records for learner-initiated evidence challenges."""
import sqlalchemy as sa
from alembic import op

revision = "0010_state_projection_challenges"
down_revision = "0009_next_action_recommendations"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("evidence_challenges",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("learner_id", sa.String(160), nullable=False),
        sa.Column("evidence_id", sa.String(160), sa.ForeignKey("evidence.id"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidence_challenges_owner", "evidence_challenges", ["learner_id", "evidence_id", "created_at"])

def downgrade():
    op.drop_index("ix_evidence_challenges_owner", table_name="evidence_challenges")
    op.drop_table("evidence_challenges")
