"""Durable, leased Learn and Quiz commands; reuse existing artifact tables."""
import sqlalchemy as sa
from alembic import op

revision = "0006_learning_workflows"
down_revision = "0005_material_context"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("learning_jobs",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("owner_id", sa.String(160), nullable=False),
        sa.Column("target_id", sa.String(160), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("command_key", sa.String(200), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("lease", sa.String(160)),
        sa.Column("expires", sa.Float()),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("result", sa.Text()),
        sa.UniqueConstraint("owner_id", "command_key"))
    op.create_index("ix_learning_job_target", "learning_jobs", ["owner_id", "target_id", "status"])


def downgrade():
    op.drop_table("learning_jobs")
