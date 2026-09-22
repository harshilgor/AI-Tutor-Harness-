"""Independent retention worker for web evidence TTL cleanup.

Run on a schedule outside the learner request path:

    python -m backend.app.web_evidence.retention_job

Or from the backend package root:

    python -m app.web_evidence.retention_job

Exit codes: 0 success, 1 failure. Emits structured logs only (no secrets, no excerpts).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from uuid import uuid4

from dotenv import load_dotenv

logger = logging.getLogger("ai_tutor.web_evidence.retention_job")


def main(argv: list[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    limit = 500
    for i, arg in enumerate(argv):
        if arg == "--limit" and i + 1 < len(argv):
            try:
                limit = max(1, int(argv[i + 1]))
            except ValueError:
                limit = 500

    # Match server startup: prefer backend/.env when present.
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    load_dotenv(os.path.join(backend_root, ".env"), override=False)

    correlation_id = f"retention_{uuid4().hex[:16]}"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    try:
        from backend.app.storage import Store
        from backend.app.database import database_url
        from backend.app.web_evidence.config import load_web_evidence_config
        from backend.app.web_evidence.retention import EvidenceRetention
        from backend.app.web_evidence.readiness import check_schema
    except ModuleNotFoundError:
        from app.storage import Store
        from app.database import database_url
        from app.web_evidence.config import load_web_evidence_config
        from app.web_evidence.retention import EvidenceRetention
        from app.web_evidence.readiness import check_schema

    config = load_web_evidence_config()
    store = Store(database_url())
    retention = EvidenceRetention(store)
    try:
        schema_ok, missing_tables, missing_indexes = check_schema(store)
        if not schema_ok:
            detail = {
                "correlationId": correlation_id,
                "missingTables": list(missing_tables),
                "missingIndexes": list(missing_indexes),
            }
            logger.error("web_evidence_retention_failed %s", json.dumps(detail, separators=(",", ":")))
            retention.record_heartbeat(
                ok=False,
                error="schema_incomplete",
                correlation_id=correlation_id,
            )
            return 1

        stats = retention.purge_expired(limit=limit, record_heartbeat=True)
        # Overwrite heartbeat with correlation id for ops correlation.
        retention.record_heartbeat(ok=True, stats=stats, correlation_id=correlation_id)
        logger.info(
            "web_evidence_retention_summary %s",
            json.dumps(
                {
                    "correlationId": correlation_id,
                    "enabled": bool(config.enabled),
                    "stats": stats,
                    "limit": limit,
                },
                separators=(",", ":"),
            ),
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "web_evidence_retention_failed %s",
            json.dumps(
                {
                    "correlationId": correlation_id,
                    "error": type(exc).__name__,
                },
                separators=(",", ":"),
            ),
        )
        try:
            retention.record_heartbeat(
                ok=False,
                error=type(exc).__name__,
                correlation_id=correlation_id,
            )
        except Exception:
            pass
        return 1
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
