"""Idempotent concept extraction from lessons / study-note sections into memory."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import text

from ..models import utc_now
from . import memory as memory_store
from .prompts import CONCEPT_EXTRACT_V1

log = logging.getLogger(__name__)


class ExtractedConcept(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=500)
    related_to: list[str] = Field(default_factory=list)


class ExtractedBundle(BaseModel):
    concepts: list[ExtractedConcept] = Field(default_factory=list)


def _canonical(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", title.strip().lower()).strip("_")[:80]


def _content_hash(text_value: str) -> str:
    return hashlib.sha256(text_value.encode("utf-8")).hexdigest()


class ConceptSyncService:
    def __init__(self, store, provider):
        self.store = store
        self.provider = provider

    def sync_from_text(
        self,
        owner: str,
        *,
        source_key: str,
        text_value: str,
        graph_id: str,
        graph_version: int,
        source_lesson_id: str | None = None,
        source_session_id: str | None = None,
        source_section_id: str | None = None,
        parent_concept_id: str | None = None,
    ) -> dict[str, Any]:
        digest = _content_hash(text_value)
        with self.store.engine.connect() as conn:
            existing = conn.execute(text("""
                SELECT id, status, result_json FROM concept_sync_runs
                WHERE learner_id=:owner AND source_key=:key AND content_hash=:hash
            """), {"owner": owner, "key": source_key, "hash": digest}).mappings().first()
        if existing and existing["status"] == "completed":
            return json.loads(existing["result_json"])

        run_id = existing["id"] if existing else f"concept_sync_{uuid4().hex}"
        now = utc_now()
        with self.store.transaction() as conn:
            memory_store.ensure_learner(conn, owner)
            if not existing:
                conn.execute(text("""
                    INSERT INTO concept_sync_runs(id, learner_id, source_key, content_hash, status, result_json, created_at, updated_at)
                    VALUES (:id, :owner, :key, :hash, 'running', '{}', :now, :now)
                """), {"id": run_id, "owner": owner, "key": source_key, "hash": digest, "now": now})
            else:
                conn.execute(text("""
                    UPDATE concept_sync_runs SET status='running', updated_at=:now WHERE id=:id
                """), {"id": run_id, "now": now})

        graph = self.store.get_graph(graph_id)
        if graph is None:
            result = {"status": "failed", "reason": "graph_not_found", "conceptIds": []}
            self._finish(owner, run_id, "failed", result)
            return result

        extracted = self._extract(text_value, graph)
        matched_ids: list[str] = []

        by_title = {_canonical(c.title): c for c in graph.concepts}
        # Prefer exact title matches; also seed every existing graph concept mentioned in text.

        for item in extracted:
            key = _canonical(item.title)
            if not key:
                continue
            if key in by_title:
                concept = by_title[key]
                matched_ids.append(concept.id)
                concept_id = concept.id
            else:
                # V1: do not fork curriculum graphs. Keep unmatched titles for later.
                continue

            with self.store.transaction() as conn:
                memory_store.seed_memory(
                    conn, learner_id=owner, concept_id=concept_id, graph_id=graph_id,
                    graph_version=graph_version,
                    source_lesson_id=source_lesson_id, source_session_id=source_session_id,
                    source_section_id=source_section_id,
                )
                if parent_concept_id and parent_concept_id != concept_id:
                    memory_store.upsert_relationship(
                        conn, learner_id=owner, source_concept_id=parent_concept_id,
                        target_concept_id=concept_id, relationship_type="part_of",
                        provenance={"sourceKey": source_key},
                    )

        # Also seed the parent concept when provided.
        if parent_concept_id:
            with self.store.transaction() as conn:
                memory_store.seed_memory(
                    conn, learner_id=owner, concept_id=parent_concept_id, graph_id=graph_id,
                    graph_version=graph_version, source_lesson_id=source_lesson_id,
                    source_session_id=source_session_id, source_section_id=source_section_id,
                )

        result = {
            "status": "completed",
            "conceptIds": list(dict.fromkeys(matched_ids + ([parent_concept_id] if parent_concept_id else []))),
            "createdIds": [],
            "matchedIds": matched_ids,
        }
        self._finish(owner, run_id, "completed", result)
        log.info("concept_sync completed owner=%s source=%s matched=%s", owner, source_key, len(matched_ids))
        return result

    def _finish(self, owner: str, run_id: str, status: str, result: dict[str, Any]) -> None:
        with self.store.transaction() as conn:
            conn.execute(text("""
                UPDATE concept_sync_runs SET status=:status, result_json=:result, updated_at=:now WHERE id=:id AND learner_id=:owner
            """), {"status": status, "result": json.dumps(result), "now": utc_now(), "id": run_id, "owner": owner})

    def _extract(self, text_value: str, graph: GraphVersion) -> list[ExtractedConcept]:
        if self.provider is None:
            return self._heuristic_extract(text_value, graph)
        try:
            raw = self.provider.complete_json(
                CONCEPT_EXTRACT_V1 + "\n" + json.dumps({
                    "schema": ExtractedBundle.model_json_schema(),
                    "existing_concepts": [{"id": c.id, "title": c.title} for c in graph.concepts],
                    "source": text_value[:6000],
                }, ensure_ascii=False),
                1600,
            )
            bundle = ExtractedBundle.model_validate(raw)
            return bundle.concepts[:8]
        except Exception:
            return self._heuristic_extract(text_value, graph)

    def _heuristic_extract(self, text_value: str, graph: GraphVersion) -> list[ExtractedConcept]:
        # Prefer existing graph concepts mentioned in the text; otherwise take section-like headings.
        found: list[ExtractedConcept] = []
        lower = text_value.lower()
        for concept in graph.concepts:
            if concept.title.lower() in lower:
                found.append(ExtractedConcept(title=concept.title, description=concept.summary or concept.title))
        if found:
            return found[:8]
        headings = re.findall(r"(?m)^#{1,3}\s+(.+)$", text_value)
        for heading in headings[:6]:
            found.append(ExtractedConcept(title=heading.strip()[:120], description=heading.strip()[:200]))
        if not found and graph.concepts:
            primary = graph.concepts[0]
            found.append(ExtractedConcept(title=primary.title, description=primary.summary or primary.title))
        return found[:8]

    def backfill(self, owner: str) -> dict[str, Any]:
        """Seed memory from study-note provenance and prior evidence without blocking."""
        seeded = 0
        with self.store.transaction() as conn:
            memory_store.ensure_learner(conn, owner)
            rows = conn.execute(text("""
                SELECT DISTINCT graph_concept_id, note_id, section_id, concept_title
                FROM note_section_provenance
                WHERE owner_id=:owner AND graph_concept_id IS NOT NULL AND tombstoned=0
            """), {"owner": owner}).mappings().all()
            evidence_rows = conn.execute(text("""
                SELECT DISTINCT concept_id, graph_id, graph_version FROM evidence
                WHERE learner_id=:owner AND admission_status='accepted'
            """), {"owner": owner}).mappings().all()

        for row in evidence_rows:
            with self.store.transaction() as conn:
                before = memory_store.get_memory(conn, owner, row["concept_id"])
                memory_store.seed_memory(
                    conn, learner_id=owner, concept_id=row["concept_id"],
                    graph_id=row["graph_id"], graph_version=row["graph_version"],
                )
                if before is None:
                    seeded += 1

        for row in rows:
            concept_id = row["graph_concept_id"]
            # Find a graph containing this concept.
            graph = None
            with self.store.engine.connect() as conn:
                graph_rows = conn.execute(text("SELECT id, payload FROM graph_versions")).mappings().all()
            for grow in graph_rows:
                try:
                    payload = json.loads(grow["payload"])
                    if any(c.get("id") == concept_id for c in payload.get("concepts") or []):
                        graph = self.store.get_graph(grow["id"])
                        break
                except Exception:
                    continue
            if not graph:
                continue
            with self.store.transaction() as conn:
                before = memory_store.get_memory(conn, owner, concept_id)
                memory_store.seed_memory(
                    conn, learner_id=owner, concept_id=concept_id, graph_id=graph.id,
                    graph_version=graph.version, source_section_id=row["section_id"],
                )
                if before is None:
                    seeded += 1

        return {"seeded": seeded, "status": "completed"}
