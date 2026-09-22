"""Indexes and lifecycle support for web evidence authorization lookups."""

import sqlalchemy as sa
from alembic import op

revision = "0016_web_evidence_indexes"
down_revision = "0015_web_evidence_runtime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_web_alias_auth",
        "web_evidence_aliases",
        ["owner_id", "tenant_id", "session_id", "response_bundle_id", "source_policy_fingerprint", "alias"],
    )
    op.create_index(
        "ix_web_receipt_auth",
        "web_evidence_receipts",
        ["owner_id", "tenant_id", "session_id", "source_policy_fingerprint", "expires_at"],
    )
    op.create_index(
        "ix_web_tool_inflight",
        "web_tool_calls",
        ["state", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_web_tool_inflight", table_name="web_tool_calls")
    op.drop_index("ix_web_receipt_auth", table_name="web_evidence_receipts")
    op.drop_index("ix_web_alias_auth", table_name="web_evidence_aliases")
