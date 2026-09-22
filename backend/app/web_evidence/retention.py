"""TTL cleanup and retention for temporary evidence records."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import text

from .clock import Clock, SystemClock
from .lifecycle import ToolCallState, transition
from .quota import QuotaLedger

logger = logging.getLogger("ai_tutor.web_evidence.retention")

RETENTION_STATUS_ID = "web_evidence_retention_status"
RETENTION_STATUS_KIND = "web_evidence_retention_status"


class EvidenceRetention:
    def __init__(self, store, clock: Clock | None = None):
        self.store = store
        self.clock = clock or SystemClock()

    def record_heartbeat(
        self,
        *,
        ok: bool,
        stats: dict[str, int] | None = None,
        error: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Persist last retention run for health/readiness without learner content."""
        now = self.clock.now()
        payload = {
            "ok": ok,
            "lastSuccessAt": now.isoformat() if ok else None,
            "lastAttemptAt": now.isoformat(),
            "stats": stats or {},
            "error": error,
            "correlationId": correlation_id,
        }
        if not ok:
            # Preserve prior success timestamp when a failure occurs.
            prior = self._load_status()
            if prior and prior.get("lastSuccessAt"):
                payload["lastSuccessAt"] = prior["lastSuccessAt"]
        body = json.dumps(payload, separators=(",", ":"))
        with self.store.transaction() as connection:
            connection.execute(
                text("DELETE FROM context_records WHERE id=:id AND kind=:kind"),
                {"id": RETENTION_STATUS_ID, "kind": RETENTION_STATUS_KIND},
            )
            connection.execute(
                text(
                    "INSERT INTO context_records(id, owner_id, kind, session_id, sequence, payload) "
                    "VALUES(:id, :owner, :kind, NULL, 0, :payload)"
                ),
                {
                    "id": RETENTION_STATUS_ID,
                    "owner": "system",
                    "kind": RETENTION_STATUS_KIND,
                    "payload": body,
                },
            )

    def _load_status(self) -> dict | None:
        with self.store.engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT payload FROM context_records WHERE id=:id AND kind=:kind"
                ),
                {"id": RETENTION_STATUS_ID, "kind": RETENTION_STATUS_KIND},
            ).first()
        if row is None:
            return None
        try:
            data = json.loads(row[0])
        except Exception:
            return None
        return data if isinstance(data, dict) else None

    def purge_expired(self, *, limit: int = 500, record_heartbeat: bool = False) -> dict[str, int]:
        """Expire receipts/aliases/cache/tool-calls. Auth still rejects expired rows before purge."""
        now = self.clock.now()
        stats = {"receipts": 0, "aliases": 0, "cache": 0, "tool_calls": 0, "quotas": 0}
        with self.store.transaction() as connection:
            rows = connection.execute(
                text(
                    "SELECT id FROM web_evidence_receipts "
                    "WHERE deleted_at IS NULL AND expires_at < :now "
                    "LIMIT :limit"
                ),
                {"now": now, "limit": limit},
            ).fetchall()
            for (evidence_id,) in rows:
                connection.execute(
                    text("UPDATE web_evidence_receipts SET deleted_at=:now WHERE id=:id"),
                    {"now": now, "id": evidence_id},
                )
                alias_result = connection.execute(
                    text("DELETE FROM web_evidence_aliases WHERE evidence_id=:id"),
                    {"id": evidence_id},
                )
                stats["receipts"] += 1
                stats["aliases"] += int(alias_result.rowcount or 0)

            cache_rows = connection.execute(
                text(
                    "SELECT id, payload FROM context_records WHERE kind='web_evidence_cache' LIMIT :limit"
                ),
                {"limit": limit},
            ).fetchall()
            for cache_id, payload in cache_rows:
                try:
                    data = json.loads(payload)
                    expires = datetime.fromisoformat(data["expiresAt"])
                    if expires.tzinfo is None:
                        expires = expires.replace(tzinfo=timezone.utc)
                    if expires < now:
                        connection.execute(
                            text("DELETE FROM context_records WHERE id=:id AND kind='web_evidence_cache'"),
                            {"id": cache_id},
                        )
                        stats["cache"] += 1
                except Exception:
                    connection.execute(
                        text("DELETE FROM context_records WHERE id=:id AND kind='web_evidence_cache'"),
                        {"id": cache_id},
                    )
                    stats["cache"] += 1

            stuck = connection.execute(
                text(
                    "SELECT id, owner_id, state FROM web_tool_calls "
                    "WHERE state IN ('authorized','running') AND updated_at < :cutoff "
                    "LIMIT :limit"
                ),
                {"cutoff": datetime.fromtimestamp(now.timestamp() - 300, tz=timezone.utc), "limit": limit},
            ).fetchall()
            for tool_call_id, owner_id, state in stuck:
                try:
                    nxt = transition(ToolCallState(state), ToolCallState.cancelled)
                except ValueError:
                    nxt = ToolCallState.cancelled
                connection.execute(
                    text(
                        "UPDATE web_tool_calls SET state=:state, updated_at=:ts "
                        "WHERE id=:id AND owner_id=:owner"
                    ),
                    {"state": nxt.value, "ts": now, "id": tool_call_id, "owner": owner_id},
                )
                stats["tool_calls"] += 1

        stats["quotas"] = QuotaLedger(self.store, clock=self.clock).reconcile_abandoned(grace_seconds=300)
        if record_heartbeat:
            self.record_heartbeat(ok=True, stats=stats)
            logger.info(
                "web_evidence_retention_ok %s",
                json.dumps({"stats": stats, "limit": limit}, separators=(",", ":")),
            )
        return stats
