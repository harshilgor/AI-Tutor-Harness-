"""Durable materials, source blocks, context and practice records."""
import sqlalchemy as sa
from alembic import op

revision = "0005_material_context"
down_revision = "0004_teaching_policy"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("materials",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("owner_id", sa.String(160), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("role", sa.String(40), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_material_owner", "materials", ["owner_id"])
    op.create_table("material_versions",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("material_id", sa.String(160), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("object_key", sa.String(200), nullable=False),
        sa.Column("sha256", sa.String(64)),
        sa.Column("media_type", sa.String(80), nullable=False),
        sa.Column("byte_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.UniqueConstraint("material_id", "version"))
    op.create_table("material_blocks",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("version_id", sa.String(160), sa.ForeignKey("material_versions.id"), nullable=False),
        sa.Column("page_index", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.UniqueConstraint("version_id", "ordinal"))
    op.create_index("ix_blocks_version", "material_blocks", ["version_id", "ordinal"])
    op.create_table("material_attachments",
        sa.Column("session_id", sa.String(160), sa.ForeignKey("learning_sessions.id"), primary_key=True),
        sa.Column("version_id", sa.String(160), sa.ForeignKey("material_versions.id"), primary_key=True))
    op.create_table("material_jobs",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("owner_id", sa.String(160), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("target_id", sa.String(160), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lease", sa.String(160)),
        sa.Column("expires", sa.Float()),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.UniqueConstraint("kind", "target_id"))
    op.create_index("ix_material_job_claim", "material_jobs", ["status", "expires"])
    # Versioned application records retain typed payloads; relational ownership
    # and kind are mandatory before any payload is made visible.
    op.create_table("context_records",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("owner_id", sa.String(160), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("session_id", sa.String(160)),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload", sa.Text(), nullable=False))
    op.create_index("ix_context_session", "context_records", ["owner_id", "session_id", "kind", "sequence"])
    op.create_table("practice_records",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("owner_id", sa.String(160), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("parent_id", sa.String(160)),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("payload", sa.Text(), nullable=False))
    op.create_table("item_solutions",
        sa.Column("item_id", sa.String(160), sa.ForeignKey("practice_records.id"), primary_key=True),
        sa.Column("payload", sa.Text(), nullable=False))
    op.create_table("material_commands",
        sa.Column("owner_id", sa.String(160), primary_key=True),
        sa.Column("operation", sa.String(80), primary_key=True),
        sa.Column("key", sa.String(200), primary_key=True),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("result_id", sa.String(160), nullable=False))


def downgrade():
    for table in ("material_commands", "item_solutions", "practice_records", "context_records",
                  "material_jobs", "material_attachments", "material_blocks", "material_versions", "materials"):
        op.drop_table(table)
