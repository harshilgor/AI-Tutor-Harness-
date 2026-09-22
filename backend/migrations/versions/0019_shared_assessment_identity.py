"""Additive shared assessment identity and exposure metadata."""

import sqlalchemy as sa
from alembic import op

revision = "0019_shared_assessment_identity"
down_revision = "0018_session_authority"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    exposure_columns = {column["name"] for column in inspector.get_columns("assessment_item_exposure")}
    additions = (
        ("item_version", sa.Integer()),
        ("last_presentation_id", sa.String(160)),
        ("origin", sa.String(40)),
    )
    for name, column_type in additions:
        if name not in exposure_columns:
            op.add_column("assessment_item_exposure", sa.Column(name, column_type, nullable=True))

    tables = set(inspector.get_table_names())
    if "assessment_presentation_links" not in tables:
        op.create_table(
            "assessment_presentation_links",
            sa.Column("presentation_id", sa.String(160), primary_key=True),
            sa.Column("workflow_kind", sa.String(40), nullable=False),
            sa.Column("workflow_id", sa.String(160), nullable=False),
            sa.Column("review_item_id", sa.String(160)),
            sa.Column("item_id", sa.String(160), nullable=False),
            sa.Column("item_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("origin", sa.String(40), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "ix_assessment_presentation_workflow",
            "assessment_presentation_links",
            ["workflow_kind", "workflow_id"],
        )
        op.create_index(
            "ix_assessment_presentation_review_item",
            "assessment_presentation_links",
            ["review_item_id"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "assessment_presentation_links" in tables:
        op.drop_index("ix_assessment_presentation_review_item", table_name="assessment_presentation_links")
        op.drop_index("ix_assessment_presentation_workflow", table_name="assessment_presentation_links")
        op.drop_table("assessment_presentation_links")

    exposure_columns = {column["name"] for column in inspector.get_columns("assessment_item_exposure")}
    for name in ("origin", "last_presentation_id", "item_version"):
        if name in exposure_columns:
            op.drop_column("assessment_item_exposure", name)
