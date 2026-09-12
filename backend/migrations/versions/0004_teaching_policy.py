"""Preserve teaching policy persistence on SQLite and PostgreSQL."""

import sqlalchemy as sa
from alembic import op

revision = "0004_teaching_policy"
down_revision = "0003_durable_session_position"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Main-branch SQLite databases already contain these tables and their data.
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "teaching_plans" not in tables:
        op.create_table(
            "teaching_plans",
            sa.Column("id", sa.String(160), primary_key=True),
            sa.Column("action_id", sa.String(160), sa.ForeignKey("learning_actions.id"), nullable=False, unique=True),
            sa.Column("payload", sa.Text(), nullable=False),
        )
    if "policy_validation_results" not in tables:
        op.create_table(
            "policy_validation_results",
            sa.Column("id", sa.String(160), primary_key=True),
            sa.Column("action_id", sa.String(160), sa.ForeignKey("learning_actions.id"), nullable=False, unique=True),
            sa.Column("plan_id", sa.String(160), sa.ForeignKey("teaching_plans.id"), nullable=False, unique=True),
            sa.Column("payload", sa.Text(), nullable=False),
        )


def downgrade() -> None:
    pass  # Preserve policy history, including tables adopted from legacy SQLite.
