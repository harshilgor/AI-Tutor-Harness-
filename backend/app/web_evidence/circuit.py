"""Provider circuit breaker with tenant-scoped open state."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import text

from .clock import Clock, SystemClock


class CircuitOpen(Exception):
    def __init__(self, provider: str, retry_after_seconds: float):
        super().__init__(provider)
        self.provider = provider
        self.retry_after_seconds = retry_after_seconds


class ProviderCircuitBreaker:
    def __init__(
        self,
        store,
        *,
        failure_threshold: int = 5,
        open_seconds: int = 60,
        clock: Clock | None = None,
    ):
        self.store = store
        self.failure_threshold = failure_threshold
        self.open_seconds = open_seconds
        self.clock = clock or SystemClock()

    def guard(self, provider_name: str, tenant_id: str) -> None:
        now = self.clock.now()
        with self.store.engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT failure_count, opened_until FROM web_provider_circuit "
                    "WHERE provider_name=:p AND tenant_id=:t"
                ),
                {"p": provider_name, "t": tenant_id},
            ).first()
        if row is None:
            return
        opened_until = row[1]
        if opened_until is not None:
            if getattr(opened_until, "tzinfo", None) is None:
                from datetime import timezone
                opened_until = opened_until.replace(tzinfo=timezone.utc)
            if opened_until > now:
                retry = (opened_until - now).total_seconds()
                raise CircuitOpen(provider_name, retry)

    def record_success(self, provider_name: str, tenant_id: str) -> None:
        now = self.clock.now()
        with self.store.transaction() as connection:
            connection.execute(
                text(
                    "INSERT INTO web_provider_circuit(provider_name, tenant_id, failure_count, opened_until, updated_at) "
                    "VALUES(:p,:t,0,NULL,:ts) "
                    "ON CONFLICT(provider_name, tenant_id) DO UPDATE SET failure_count=0, opened_until=NULL, updated_at=:ts"
                ),
                {"p": provider_name, "t": tenant_id, "ts": now},
            )

    def record_failure(self, provider_name: str, tenant_id: str) -> None:
        now = self.clock.now()
        with self.store.transaction() as connection:
            row = connection.execute(
                text(
                    "SELECT failure_count FROM web_provider_circuit "
                    "WHERE provider_name=:p AND tenant_id=:t"
                ),
                {"p": provider_name, "t": tenant_id},
            ).first()
            failures = int(row[0]) + 1 if row else 1
            opened_until = None
            if failures >= self.failure_threshold:
                opened_until = now + timedelta(seconds=self.open_seconds)
            if row:
                connection.execute(
                    text(
                        "UPDATE web_provider_circuit SET failure_count=:f, opened_until=:o, updated_at=:ts "
                        "WHERE provider_name=:p AND tenant_id=:t"
                    ),
                    {"f": failures, "o": opened_until, "ts": now, "p": provider_name, "t": tenant_id},
                )
            else:
                connection.execute(
                    text(
                        "INSERT INTO web_provider_circuit(provider_name, tenant_id, failure_count, opened_until, updated_at) "
                        "VALUES(:p,:t,:f,:o,:ts)"
                    ),
                    {"p": provider_name, "t": tenant_id, "f": failures, "o": opened_until, "ts": now},
                )
