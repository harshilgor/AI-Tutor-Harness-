"""Atomic quota reservation with crash-safe finalization.

Cross-worker safety comes from the shared DB ledger and conditional updates,
not from the process-local semaphore (which is only a local optimization).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text

from .clock import Clock, SystemClock


@dataclass
class QuotaReservation:
    scope_key: str
    scope_kind: str
    window_start: str
    units: int
    committed: bool = False
    released: bool = False


class QuotaExceeded(Exception):
    def __init__(self, scope_kind: str):
        super().__init__(scope_kind)
        self.scope_kind = scope_kind


class QuotaLedger:
    def __init__(self, store, clock: Clock | None = None):
        self.store = store
        self.clock = clock or SystemClock()

    def _window(self, kind: str) -> str:
        now = self.clock.now()
        if kind.endswith("_day") or kind in {"user_day", "tenant_day", "global_day"}:
            return now.date().isoformat()
        if kind.endswith("_session") or kind == "session":
            return "session"
        if kind.endswith("_turn") or kind == "turn":
            return "turn"
        return now.date().isoformat()

    def reserve(self, *, scope_key: str, scope_kind: str, limit: int, units: int = 1) -> QuotaReservation:
        """Atomically reserve units. Safe across workers sharing the same database."""
        if limit <= 0 or units <= 0 or units > limit:
            raise QuotaExceeded(scope_kind)
        window = self._window(scope_kind)
        now = self.clock.now()
        with self.store.transaction() as connection:
            # Serialize contending workers on this ledger row.
            connection.execute(text("SELECT 1")).first()
            row = connection.execute(
                text(
                    "SELECT reserved, consumed FROM web_quota_ledgers "
                    "WHERE scope_key=:key AND window_start=:window"
                ),
                {"key": scope_key, "window": window},
            ).first()
            if row is None:
                try:
                    connection.execute(
                        text(
                            "INSERT INTO web_quota_ledgers("
                            "scope_key, scope_kind, window_start, reserved, consumed, updated_at"
                            ") VALUES (:key,:kind,:window,:reserved,0,:ts)"
                        ),
                        {
                            "key": scope_key,
                            "kind": scope_kind,
                            "window": window,
                            "reserved": units,
                            "ts": now,
                        },
                    )
                except Exception:
                    # Concurrent insert won; fall through to conditional update.
                    result = connection.execute(
                        text(
                            "UPDATE web_quota_ledgers SET reserved=reserved+:u, updated_at=:ts "
                            "WHERE scope_key=:key AND window_start=:window AND reserved+:u <= :limit"
                        ),
                        {"u": units, "ts": now, "key": scope_key, "window": window, "limit": limit},
                    )
                    if result.rowcount != 1:
                        raise QuotaExceeded(scope_kind)
            else:
                result = connection.execute(
                    text(
                        "UPDATE web_quota_ledgers SET reserved=reserved+:u, updated_at=:ts "
                        "WHERE scope_key=:key AND window_start=:window AND reserved+:u <= :limit"
                    ),
                    {"u": units, "ts": now, "key": scope_key, "window": window, "limit": limit},
                )
                if result.rowcount != 1:
                    raise QuotaExceeded(scope_kind)
        return QuotaReservation(
            scope_key=scope_key,
            scope_kind=scope_kind,
            window_start=window,
            units=units,
        )

    def commit(self, reservation: QuotaReservation) -> None:
        if reservation.committed or reservation.released:
            return
        now = self.clock.now()
        with self.store.transaction() as connection:
            connection.execute(
                text(
                    "UPDATE web_quota_ledgers SET consumed=consumed+:u, updated_at=:ts "
                    "WHERE scope_key=:key AND window_start=:window"
                ),
                {
                    "u": reservation.units,
                    "ts": now,
                    "key": reservation.scope_key,
                    "window": reservation.window_start,
                },
            )
        reservation.committed = True

    def release(self, reservation: QuotaReservation) -> None:
        if reservation.committed or reservation.released:
            return
        now = self.clock.now()
        with self.store.transaction() as connection:
            connection.execute(
                text(
                    "UPDATE web_quota_ledgers SET "
                    "reserved=CASE WHEN reserved>=:u THEN reserved-:u ELSE 0 END, "
                    "updated_at=:ts WHERE scope_key=:key AND window_start=:window"
                ),
                {
                    "u": reservation.units,
                    "ts": now,
                    "key": reservation.scope_key,
                    "window": reservation.window_start,
                },
            )
        reservation.released = True

    def reconcile_abandoned(self, *, grace_seconds: int = 300) -> int:
        """Release reserved-but-unconsumed units for ledgers with no in-flight tool calls.

        After a worker crash, `reserved` can exceed `consumed` with no live holder.
        This clamps abandoned headroom once the grace window elapses and no tool call
        remains in authorized/running state.
        """
        now = self.clock.now()
        cutoff = now.timestamp() - grace_seconds
        released = 0
        with self.store.transaction() as connection:
            inflight = connection.execute(
                text(
                    "SELECT COUNT(*) FROM web_tool_calls "
                    "WHERE state IN ('authorized','running')"
                )
            ).scalar()
            if int(inflight or 0) > 0:
                return 0
            rows = connection.execute(
                text(
                    "SELECT scope_key, window_start, reserved, consumed, updated_at "
                    "FROM web_quota_ledgers WHERE reserved > consumed"
                )
            ).fetchall()
            for row in rows:
                updated = row[4]
                if updated is None:
                    continue
                ts = updated.timestamp() if hasattr(updated, "timestamp") else cutoff
                if ts > cutoff:
                    continue
                delta = int(row[2]) - int(row[3])
                if delta <= 0:
                    continue
                connection.execute(
                    text(
                        "UPDATE web_quota_ledgers SET reserved=consumed, updated_at=:ts "
                        "WHERE scope_key=:key AND window_start=:window AND reserved > consumed"
                    ),
                    {"ts": now, "key": row[0], "window": row[1]},
                )
                released += delta
        return released
