"""Durable generation records and replayable stream events."""
from __future__ import annotations

import hashlib
import json
import time
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .generation_models import GenerationDescriptor
from .generation_models import GenerationEvent
from .material_service import problem

TERMINAL = {"completed", "cancelled", "failed", "interrupted"}
ACTIVE = {"queued", "preparing", "streaming", "finalizing", "cancel_requested"}
TRANSITIONS = {
    "queued": {"preparing", "cancel_requested", "failed", "interrupted"},
    "preparing": {"streaming", "cancel_requested", "failed", "interrupted"},
    "streaming": {"finalizing", "cancel_requested", "failed", "interrupted"},
    "finalizing": {"completed", "failed", "interrupted"},
    "cancel_requested": {"cancelled", "failed", "interrupted"},
}


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


class GenerationStore:
    def __init__(self, store):
        self.store = store

    def _row(self, row) -> dict:
        if not row:
            problem("not_found", "This generation is not available.", 404)
        payload = json.loads(row["payload"])
        result = json.loads(row["result"]) if row["result"] else None
        return {**payload, "id": row["id"], "status": row["status"], "sequence": row["sequence"],
                "cancellationRequested": bool(row["cancellation_requested"]), "provider": row["provider"],
                "model": row["model"], "errorCode": row["error_code"], "result": result}

    def create(self, owner: str, session_id: str, request: dict, key: str, provider: str, model: str, on_create=None) -> dict:
        request_hash = hashlib.sha256(_json([session_id, request]).encode()).hexdigest()
        now = time.time()
        record = {"id": f"gen_{uuid4().hex}", "owner": owner, "session": session_id, "mode": request["mode"], "request": request, "createdAt": now, "metrics": {"queuedAt": now}}
        values = {"id": record["id"], "owner": owner, "session": session_id, "key": key, "hash": request_hash,
                  "mode": request["mode"], "provider": provider, "model": model, "payload": _json(record), "now": now}
        try:
            with self.store.transaction() as conn:
                conn.execute(text("INSERT INTO generation_records(id,owner_id,session_id,idempotency_key,request_hash,status,mode,provider,model,payload,created_at,updated_at) VALUES(:id,:owner,:session,:key,:hash,'queued',:mode,:provider,:model,:payload,:now,:now)"), values)
                if on_create is not None:
                    journey_revision = on_create(conn, record["id"])
                    record["journeyRevision"] = journey_revision
                    conn.execute(text("UPDATE generation_records SET payload=:payload WHERE id=:id"), {"id": record["id"], "payload": _json(record)})
        except IntegrityError:
            with self.store.engine.connect() as conn:
                existing = conn.execute(text("SELECT * FROM generation_records WHERE owner_id=:owner AND idempotency_key=:key"), values).mappings().first()
                active = conn.execute(text("""
                    SELECT id FROM generation_records WHERE owner_id=:owner AND session_id=:session
                    AND status IN ('queued','preparing','streaming','finalizing','cancel_requested')
                    LIMIT 1
                """), values).first()
            if not existing and active:
                problem("generation_in_progress", "Finish or cancel the current response before sending another message.", 409)
            if not existing or existing["request_hash"] != request_hash:
                problem("idempotency_conflict", "This request key was already used for another generation.", 409)
            return self._row(existing)
        return self.get(owner, record["id"])

    def get(self, owner: str, generation_id: str) -> dict:
        with self.store.engine.connect() as conn:
            row = conn.execute(text("SELECT * FROM generation_records WHERE id=:id AND owner_id=:owner"), {"id": generation_id, "owner": owner}).mappings().first()
        return self._row(row)

    def transition(self, generation_id: str, status: str, *, error_code: str | None = None, sequence: int | None = None, result: dict | None = None, connection=None) -> dict:
        if connection is None:
            with self.store.transaction() as conn:
                return self.transition(generation_id, status, error_code=error_code, sequence=sequence, result=result, connection=conn)
        row = connection.execute(text("SELECT * FROM generation_records WHERE id=:id"), {"id": generation_id}).mappings().first()
        if not row:
            raise RuntimeError("Missing generation")
        current = row["status"]
        if status not in TRANSITIONS.get(current, set()):
            raise RuntimeError(f"Illegal generation transition {current} -> {status}")
        values = {"id": generation_id, "status": status, "now": time.time(), "error": error_code,
                  "sequence": max(int(row["sequence"]), sequence or 0), "result": _json(result) if result is not None else row["result"]}
        updated = connection.execute(text("""
            UPDATE generation_records SET status=:status,updated_at=:now,error_code=:error,
                sequence=:sequence,result=:result WHERE id=:id AND status=:previous
        """), {**values, "previous": current})
        if updated.rowcount != 1:
            raise RuntimeError("Generation changed before its transition could be committed")
        return self._row(connection.execute(text("SELECT * FROM generation_records WHERE id=:id"), {"id": generation_id}).mappings().one())

    def request_cancel(self, owner: str, generation_id: str) -> dict:
        with self.store.transaction() as conn:
            row = conn.execute(text("SELECT * FROM generation_records WHERE id=:id AND owner_id=:owner"), {"id": generation_id, "owner": owner}).mappings().first()
            state = self._row(row)
            if state["status"] in TERMINAL:
                return state
            conn.execute(text("UPDATE generation_records SET cancellation_requested=1,status=CASE WHEN status IN ('queued','preparing','streaming') THEN 'cancel_requested' ELSE status END,updated_at=:now WHERE id=:id"), {"id": generation_id, "now": time.time()})
            return self._row(conn.execute(text("SELECT * FROM generation_records WHERE id=:id"), {"id": generation_id}).mappings().one())

    def update_metrics(self, generation_id: str, values: dict, connection=None) -> None:
        if connection is None:
            with self.store.transaction() as conn:
                self.update_metrics(generation_id, values, conn)
                return
        row = connection.execute(text("SELECT payload FROM generation_records WHERE id=:id"), {"id": generation_id}).first()
        if not row:
            raise RuntimeError("Missing generation")
        payload = json.loads(row[0]); payload.setdefault("metrics", {}).update(values)
        connection.execute(text("UPDATE generation_records SET payload=:payload,updated_at=:now WHERE id=:id"), {"id": generation_id, "payload": _json(payload), "now": time.time()})

    def cancelled(self, generation_id: str) -> bool:
        with self.store.engine.connect() as conn:
            row = conn.execute(text("SELECT cancellation_requested FROM generation_records WHERE id=:id"), {"id": generation_id}).first()
        return bool(row and row[0])

    def append_event(self, generation_id: str, event_type: str, data: dict | None = None, connection=None) -> GenerationEvent:
        if connection is None:
            with self.store.transaction() as conn:
                return self.append_event(generation_id, event_type, data, conn)
        row = connection.execute(text("UPDATE generation_records SET sequence=sequence+1 WHERE id=:id RETURNING sequence"), {"id": generation_id}).first()
        if row is None:
            raise RuntimeError("Missing generation")
        sequence = int(row[0])
        connection.execute(text("INSERT INTO generation_events(generation_id,sequence,event_type,data_json,created_at) VALUES(:id,:sequence,:type,:data,:now)"),
                           {"id": generation_id, "sequence": sequence, "type": event_type, "data": _json(data or {}), "now": time.time()})
        return GenerationEvent(generation_id=generation_id, sequence=sequence, type=event_type, data=data or {})

    def events_after(self, generation_id: str, after: int) -> list[GenerationEvent]:
        with self.store.engine.connect() as conn:
            rows = conn.execute(text("SELECT sequence,event_type,data_json FROM generation_events WHERE generation_id=:id AND sequence>:after ORDER BY sequence"),
                                {"id": generation_id, "after": after}).mappings().all()
        return [GenerationEvent(generation_id=generation_id, sequence=row["sequence"], type=row["event_type"], data=json.loads(row["data_json"])) for row in rows]

    def interrupt_active(self) -> None:
        from .journey_service import JourneyService
        journey_service = JourneyService(self.store, None)
        with self.store.transaction() as conn:
            rows = conn.execute(text("SELECT id,owner_id,session_id FROM generation_records WHERE status IN ('queued','preparing','streaming','finalizing','cancel_requested')")).mappings().all()
            conn.execute(text("UPDATE generation_records SET status='interrupted',error_code='STREAM_INTERRUPTED',updated_at=:now WHERE status IN ('queued','preparing','streaming','finalizing','cancel_requested')"), {"now": time.time()})
            for row in rows:
                try:
                    journey_service.finish_stream_turn(row["owner_id"], row["session_id"], row["id"], "interrupted", "STREAM_INTERRUPTED", conn)
                except Exception:
                    # Older generations predate canonical submitted turns.
                    pass
                self.append_event(row["id"], "generation.error", {"code": "STREAM_INTERRUPTED", "message": "The generation was interrupted. Please try again."}, conn)

    @staticmethod
    def descriptor(record: dict) -> GenerationDescriptor:
        result = record.get("result") or {}
        return GenerationDescriptor(id=record["id"], session_id=record["session"], mode=record["mode"], status=record["status"], sequence=record["sequence"], provider=record["provider"], model=record["model"], journey_revision=record.get("journeyRevision"), final_revision=result.get("revision"), error_code=record.get("errorCode"), metrics=record.get("metrics") or {})
