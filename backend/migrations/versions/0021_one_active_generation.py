"""Reserve one active streamed generation per learner conversation."""
import sqlalchemy as sa
from alembic import op

revision = "0021_one_active_generation"
down_revision = "0020_courses_system"
branch_labels = None
depends_on = None

ACTIVE = ("queued", "preparing", "streaming", "finalizing", "cancel_requested")


def upgrade() -> None:
    # A process restart already interrupts these rows at application startup.
    # Do it before creating the constraint so older databases can migrate.
    op.get_bind().execute(sa.text("""
        UPDATE generation_records SET status='interrupted', error_code='STREAM_INTERRUPTED'
        WHERE status IN ('queued','preparing','streaming','finalizing','cancel_requested')
    """))
    predicate = sa.column("status").in_(ACTIVE)
    op.create_index(
        "uq_generation_active_conversation", "generation_records", ["owner_id", "session_id"],
        unique=True, sqlite_where=predicate, postgresql_where=predicate,
    )


def downgrade() -> None:
    op.drop_index("uq_generation_active_conversation", table_name="generation_records")
