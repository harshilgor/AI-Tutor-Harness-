"""Durable tables for evidence tool calls, receipts, quotas, and idempotency."""

import sqlalchemy as sa
from alembic import op

revision = "0015_web_evidence_runtime"
down_revision = "0014_review_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "web_tool_calls",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("owner_id", sa.String(160), nullable=False),
        sa.Column("tenant_id", sa.String(160), nullable=False),
        sa.Column("course_id", sa.String(160)),
        sa.Column("session_id", sa.String(160), nullable=False),
        sa.Column("response_bundle_id", sa.String(160), nullable=False),
        sa.Column("tool_name", sa.String(80), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("policy_version", sa.String(80), nullable=False),
        sa.Column("feature_version", sa.String(80), nullable=False),
        sa.Column("source_policy_fingerprint", sa.String(64), nullable=False),
        sa.Column("request_id", sa.String(160)),
        sa.Column("conversation_id", sa.String(160)),
        sa.Column("trace_id", sa.String(160)),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "idempotency_key", name="uq_web_tool_idempotency"),
    )
    op.create_index("ix_web_tool_bundle", "web_tool_calls", ["owner_id", "response_bundle_id"])
    op.create_index("ix_web_tool_session_state", "web_tool_calls", ["owner_id", "session_id", "state"])

    op.create_table(
        "web_evidence_receipts",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("owner_id", sa.String(160), nullable=False),
        sa.Column("tenant_id", sa.String(160), nullable=False),
        sa.Column("course_id", sa.String(160)),
        sa.Column("session_id", sa.String(160), nullable=False),
        sa.Column("response_bundle_id", sa.String(160), nullable=False),
        sa.Column("tool_call_id", sa.String(160), nullable=False),
        sa.Column("source_policy_fingerprint", sa.String(64), nullable=False),
        sa.Column("source_kind", sa.String(40), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("provider_result_ref", sa.String(400)),
        sa.Column("trust_label", sa.String(40), nullable=False),
        sa.Column("title", sa.String(400), nullable=False),
        sa.Column("canonical_url", sa.String(1000)),
        sa.Column("domain", sa.String(300)),
        sa.Column("author", sa.String(300)),
        sa.Column("published_date", sa.String(80)),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("classification", sa.String(40), nullable=False),
        sa.Column("relevance_score", sa.Float()),
        sa.Column("span_id", sa.String(160)),
        sa.Column("version_id", sa.String(160)),
        sa.Column("page_index", sa.Integer()),
        sa.Column("open_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["tool_call_id"], ["web_tool_calls.id"]),
    )
    op.create_index(
        "ix_web_receipt_scope",
        "web_evidence_receipts",
        ["owner_id", "tenant_id", "session_id", "response_bundle_id"],
    )
    op.create_index("ix_web_receipt_expiry", "web_evidence_receipts", ["expires_at", "deleted_at"])

    op.create_table(
        "web_evidence_aliases",
        sa.Column("response_bundle_id", sa.String(160), primary_key=True),
        sa.Column("alias", sa.String(20), primary_key=True),
        sa.Column("evidence_id", sa.String(160), nullable=False),
        sa.Column("owner_id", sa.String(160), nullable=False),
        sa.Column("tenant_id", sa.String(160), nullable=False),
        sa.Column("session_id", sa.String(160), nullable=False),
        sa.Column("source_policy_fingerprint", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["evidence_id"], ["web_evidence_receipts.id"]),
    )

    op.create_table(
        "web_quota_ledgers",
        sa.Column("scope_key", sa.String(300), primary_key=True),
        sa.Column("scope_kind", sa.String(40), nullable=False),
        sa.Column("window_start", sa.String(40), primary_key=True),
        sa.Column("reserved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "web_provider_circuit",
        sa.Column("provider_name", sa.String(80), primary_key=True),
        sa.Column("tenant_id", sa.String(160), primary_key=True),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("opened_until", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("web_provider_circuit")
    op.drop_table("web_quota_ledgers")
    op.drop_table("web_evidence_aliases")
    op.drop_table("web_evidence_receipts")
    op.drop_table("web_tool_calls")
