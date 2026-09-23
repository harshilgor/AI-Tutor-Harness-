"""Add Courses system tables and course_id references to sessions, notes, and materials."""

import sqlalchemy as sa
from alembic import op

revision = "0020_courses_system"
down_revision = "0019_shared_assessment_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "courses" not in tables:
        op.create_table(
            "courses",
            sa.Column("id", sa.String(160), primary_key=True),
            sa.Column("owner_id", sa.String(120), nullable=False),
            sa.Column("name", sa.String(300), nullable=False),
            sa.Column("goal", sa.Text(), nullable=False),
            sa.Column("teaching_preferences", sa.Text(), nullable=True),
            sa.Column("reminder_preferences", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_courses_owner", "courses", ["owner_id", "updated_at"])

    if "course_roadmap_nodes" not in tables:
        op.create_table(
            "course_roadmap_nodes",
            sa.Column("id", sa.String(160), primary_key=True),
            sa.Column("course_id", sa.String(160), sa.ForeignKey("courses.id"), nullable=False),
            sa.Column("phase", sa.String(160), nullable=False),
            sa.Column("concept_id", sa.String(160), nullable=True),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("status", sa.String(40), nullable=False, server_default="planned"),
            sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_course_roadmap_course", "course_roadmap_nodes", ["course_id", "order_index"])

    # Add optional course_id to existing tables
    for table_name in ("learning_sessions", "workspace_notes", "materials"):
        if table_name in tables:
            columns = {c["name"] for c in inspector.get_columns(table_name)}
            if "course_id" not in columns:
                op.add_column(table_name, sa.Column("course_id", sa.String(160), nullable=True))
                op.create_index(f"ix_{table_name}_course", table_name, ["course_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    for table_name in ("materials", "workspace_notes", "learning_sessions"):
        if table_name in tables:
            indexes = {idx["name"] for idx in inspector.get_indexes(table_name)}
            if f"ix_{table_name}_course" in indexes:
                op.drop_index(f"ix_{table_name}_course", table_name=table_name)
            columns = {c["name"] for c in inspector.get_columns(table_name)}
            if "course_id" in columns:
                op.drop_column(table_name, "course_id")

    if "course_roadmap_nodes" in tables:
        op.drop_index("ix_course_roadmap_course", table_name="course_roadmap_nodes")
        op.drop_table("course_roadmap_nodes")

    if "courses" in tables:
        op.drop_index("ix_courses_owner", table_name="courses")
        op.drop_table("courses")
