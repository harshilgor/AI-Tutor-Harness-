"""Owned versioned artifacts and durable commands for interactive learning."""
import hashlib
import json
import time
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from .material_service import problem


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def encoded(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


class WorkflowStore:
    def __init__(self, store):
        self.store = store

    def read(self, owner, record_id, kind=None, connection=None):
        if connection is None:
            with self.store.engine.connect() as conn:
                return self.read(owner, record_id, kind, conn)
        row = connection.execute(text("SELECT * FROM practice_records WHERE id=:id AND owner_id=:owner"),
                                 {"id": record_id, "owner": owner}).mappings().first()
        if row is None or (kind and row["kind"] != kind):
            problem("not_found", "This learning activity is not available.", 404)
        return {**json.loads(row["payload"]), "id": row["id"], "revision": row["revision"]}

    def put(self, conn, owner, kind, data, parent=None, expected=None):
        values = {"id": data["id"], "owner": owner, "kind": kind, "parent": parent, "payload": encoded(data)}
        if expected is None:
            conn.execute(text("INSERT INTO practice_records(id,owner_id,kind,parent_id,revision,payload) VALUES(:id,:owner,:kind,:parent,1,:payload)"), values)
        else:
            result = conn.execute(text("UPDATE practice_records SET payload=:payload, revision=revision+1 WHERE id=:id AND owner_id=:owner AND revision=:expected"), {**values, "expected": expected})
            if result.rowcount != 1:
                problem("revision_conflict", "This activity changed. Reload it before continuing.", 409)

    def listing(self, owner, kind):
        with self.store.engine.connect() as conn:
            rows = conn.execute(text("SELECT id FROM practice_records WHERE owner_id=:owner AND kind=:kind ORDER BY id"), {"owner": owner, "kind": kind}).all()
            return [self.read(owner, row[0], kind, conn) for row in rows]

    def enqueue(self, owner, target, kind, payload, key):
        request_hash = hashlib.sha256(encoded([target, kind, payload]).encode()).hexdigest()
        values = {"id": uid("job"), "owner": owner, "target": target, "kind": kind, "key": key,
                  "hash": request_hash, "payload": encoded(payload)}
        try:
            with self.store.transaction() as conn:
                conn.execute(text("INSERT INTO learning_jobs(id,owner_id,target_id,kind,command_key,request_hash,status,payload) VALUES(:id,:owner,:target,:kind,:key,:hash,'queued',:payload)"), values)
        except IntegrityError:
            with self.store.engine.connect() as conn:
                row = conn.execute(text("SELECT id,request_hash FROM learning_jobs WHERE owner_id=:owner AND command_key=:key"), values).first()
            if not row or row[1] != request_hash:
                problem("idempotency_conflict", "This request key was already used for another action.", 409)
            values["id"] = row[0]
        return self.job(owner, values["id"])

    def job(self, owner, job_id):
        with self.store.engine.connect() as conn:
            row = conn.execute(text("SELECT id,status,result FROM learning_jobs WHERE id=:id AND owner_id=:owner"), {"id": job_id, "owner": owner}).mappings().first()
        if not row:
            problem("not_found", "This operation is not available.", 404)
        return {"id": row["id"], "status": row["status"], "result": json.loads(row["result"]) if row["result"] else None}

    def claim(self, job_id):
        lease = uid("lease")
        with self.store.transaction() as conn:
            changed = conn.execute(text("UPDATE learning_jobs SET status='running',lease=:lease,expires=:expires WHERE id=:id AND (status='queued' OR (status='running' AND expires<:now))"),
                                   {"id": job_id, "lease": lease, "expires": time.time() + 900, "now": time.time()})
            if changed.rowcount != 1:
                return None
            row = conn.execute(text("SELECT * FROM learning_jobs WHERE id=:id"), {"id": job_id}).mappings().one()
            return {**row, "payload": json.loads(row["payload"])}

    def finish(self, conn, job, result, status="completed"):
        changed = conn.execute(text("UPDATE learning_jobs SET status=:status,result=:result,lease=NULL,expires=NULL WHERE id=:id AND lease=:lease AND status='running'"),
                               {"id": job["id"], "lease": job["lease"], "status": status, "result": encoded(result)})
        if changed.rowcount != 1:
            problem("lease_lost", "This operation was resumed elsewhere.", 409)

    def cancel(self, owner, job_id):
        self.job(owner, job_id)
        with self.store.transaction() as conn:
            conn.execute(text("UPDATE learning_jobs SET status='cancelled',lease=NULL,expires=NULL WHERE id=:id AND owner_id=:owner AND status IN ('queued','running')"), {"id": job_id, "owner": owner})
        return self.job(owner, job_id)
