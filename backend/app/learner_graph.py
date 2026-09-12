"""The learner-owned knowledge graph projection.

Topic graphs describe a bounded subject.  This module maintains the separate,
long-lived graph that a learner sees across subjects.  It is deliberately a
projection: topic graphs remain authoritative for domain structure, while
learner events and future learner-state commits update the overlay.

The repository uses the existing Store connection so this first slice stays
local and transactional.  Its tables and API are isolated from the topic
graph tables, making a later PostgreSQL repository replacement straightforward.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel, Field, field_validator

from .models import GraphVersion, utc_now
from .storage import Store


LearnerNodeState = Literal[
    "unexplored",
    "explored",
    "developing",
    "demonstrated",
    "review_due",
    "misconception_detected",
]

LearnerEdgeType = Literal[
    "requires",
    "recommended_before",
    "related",
    "part_of",
    "contrasts",
    "enables",
]

LearnerEdgeStatus = Literal["supported", "proposed", "conflicting", "rejected"]


class LearnerGraphConcept(BaseModel):
    id: str
    canonical_key: str
    title: str
    definition: str
    summary: str
    source_scope_ids: list[str] = Field(default_factory=list)
    source_graph_ids: list[str] = Field(default_factory=list)
    source_concept_ids: list[str] = Field(default_factory=list)
    state: LearnerNodeState = "unexplored"
    evidence_count: int = Field(default=0, ge=0)
    last_evidence_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class LearnerGraphEdge(BaseModel):
    id: str
    source_concept_id: str
    target_concept_id: str
    type: LearnerEdgeType
    rationale: str
    source_graph_ids: list[str] = Field(default_factory=list)
    status: LearnerEdgeStatus = "proposed"
    confidence: float | None = Field(default=None, ge=0, le=1)


class LearnerGraph(BaseModel):
    id: str
    learner_id: str
    revision: int = Field(ge=0)
    state_version: int = Field(ge=0)
    concepts: list[LearnerGraphConcept] = Field(default_factory=list)
    edges: list[LearnerGraphEdge] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class LearnerGraphImportRequest(BaseModel):
    graph_id: str = Field(min_length=1, max_length=160)


class LearnerGraphEventCreate(BaseModel):
    event_type: Literal[
        "concept_explored",
        "lesson_started",
        "lesson_completed",
        "assessment_evidence",
        "concept_demonstrated",
        "concept_review_due",
        "misconception_detected",
    ]
    concept_id: str = Field(min_length=1, max_length=160)
    source_graph_id: str | None = Field(default=None, max_length=160)
    evidence_id: str | None = Field(default=None, max_length=160)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def metadata_is_bounded(cls, value: dict[str, Any]) -> dict[str, Any]:
        # Event metadata is intentionally small.  Full artifacts/evidence live
        # in their own stores and should not be copied into this projection.
        if len(value) > 24:
            raise ValueError("metadata may contain at most 24 fields")
        return value


class LearnerGraphEvent(BaseModel):
    id: str
    learner_id: str
    event_type: str
    concept_id: str
    source_graph_id: str | None = None
    evidence_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class LearnerGraphMutationResponse(BaseModel):
    graph: LearnerGraph
    event: LearnerGraphEvent


def _clean_identity(value: str) -> str:
    """Create a stable, conservative identity candidate for a concept.

    Identity resolution is not allowed to merge concepts solely on a display
    label.  Including a normalized definition/summary makes this a repeatable
    import key while leaving richer cross-domain identity resolution for the
    curriculum service.
    """

    text = re.sub(r"\s+", " ", value.strip().lower())
    text = re.sub(r"[^\w\s.-]", "", text)
    return text[:300]


def _edge_type(value: str) -> LearnerEdgeType:
    return {
        "related_to": "related",
        "recommended_before": "recommended_before",
        "requires": "requires",
        "part_of": "part_of",
        "contrasts": "contrasts",
        "enables": "enables",
    }.get(value, "related")  # type: ignore[return-value]


def _edge_status(value: str) -> LearnerEdgeStatus:
    if value == "supported":
        return "supported"
    if value == "conflicting":
        return "conflicting"
    if value == "rejected":
        return "rejected"
    return "proposed"


class LearnerGraphRepository:
    """Persistence and projection operations for one learner graph."""

    def __init__(self, db: Store):
        self.db = db
        # Store intentionally remains the narrow adapter for the existing
        # topic graph.  These tables are isolated and can move to a dedicated
        # repository without changing route contracts.
        self.connection = db._connection
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS learner_graphs (
                learner_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS learner_graph_concepts (
                learner_id TEXT NOT NULL,
                id TEXT NOT NULL,
                canonical_key TEXT NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (learner_id, id),
                UNIQUE (learner_id, canonical_key)
            );
            CREATE TABLE IF NOT EXISTS learner_graph_edges (
                learner_id TEXT NOT NULL,
                id TEXT NOT NULL,
                source_concept_id TEXT NOT NULL,
                target_concept_id TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (learner_id, id),
                UNIQUE (learner_id, source_concept_id, target_concept_id, edge_type)
            );
            CREATE TABLE IF NOT EXISTS learner_graph_events (
                id TEXT PRIMARY KEY,
                learner_id TEXT NOT NULL,
                concept_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        # Recover cleanly if an early local run created the event table before
        # its timestamp column was introduced.
        event_columns = {
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(learner_graph_events)").fetchall()
        }
        if "created_at" not in event_columns:
            self.connection.execute(
                "ALTER TABLE learner_graph_events ADD COLUMN created_at TEXT NOT NULL DEFAULT ''"
            )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_learner_graph_events_learner ON learner_graph_events(learner_id, created_at)"
        )
        self.connection.commit()

    @staticmethod
    def graph_id(learner_id: str) -> str:
        return f"learner_graph_{learner_id}"

    def _new_graph(self, learner_id: str) -> LearnerGraph:
        now = utc_now()
        return LearnerGraph(
            id=self.graph_id(learner_id),
            learner_id=learner_id,
            revision=0,
            state_version=0,
            created_at=now,
            updated_at=now,
        )

    def get_graph(self, learner_id: str) -> LearnerGraph:
        row = self.connection.execute(
            "SELECT payload FROM learner_graphs WHERE learner_id = ?", (learner_id,)
        ).fetchone()
        if row:
            return LearnerGraph.model_validate_json(row["payload"])
        graph = self._new_graph(learner_id)
        self._save_graph(graph)
        return graph

    def _save_graph(self, graph: LearnerGraph, *, commit: bool = True) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO learner_graphs(learner_id, payload) VALUES(?, ?)",
            (graph.learner_id, graph.model_dump_json()),
        )
        # Keep normalized rows for future neighborhood queries and audit tools.
        self.connection.execute(
            "DELETE FROM learner_graph_concepts WHERE learner_id = ?", (graph.learner_id,)
        )
        self.connection.executemany(
            "INSERT INTO learner_graph_concepts(learner_id, id, canonical_key, payload) VALUES(?, ?, ?, ?)",
            [
                (graph.learner_id, concept.id, concept.canonical_key, concept.model_dump_json())
                for concept in graph.concepts
            ],
        )
        self.connection.execute(
            "DELETE FROM learner_graph_edges WHERE learner_id = ?", (graph.learner_id,)
        )
        self.connection.executemany(
            "INSERT INTO learner_graph_edges(learner_id, id, source_concept_id, target_concept_id, edge_type, payload) VALUES(?, ?, ?, ?, ?, ?)",
            [
                (
                    graph.learner_id,
                    edge.id,
                    edge.source_concept_id,
                    edge.target_concept_id,
                    edge.type,
                    edge.model_dump_json(),
                )
                for edge in graph.edges
            ],
        )
        if commit:
            self.connection.commit()

    def import_topic_graph(self, learner_id: str, source: GraphVersion) -> LearnerGraphMutationResponse:
        graph = self.get_graph(learner_id)
        concepts = list(graph.concepts)
        edges = list(graph.edges)
        by_key = {concept.canonical_key: concept for concept in concepts}
        source_to_learner: dict[str, str] = {}
        changed = False

        for source_concept in source.concepts:
            canonical_key = _clean_identity(
                f"{source_concept.title} {source_concept.summary} {source_concept.objective}"
            )
            existing = by_key.get(canonical_key)
            if existing is None:
                now = utc_now()
                existing = LearnerGraphConcept(
                    id=f"learner_concept_{uuid4().hex}",
                    canonical_key=canonical_key,
                    title=source_concept.title,
                    definition=source_concept.summary,
                    summary=source_concept.summary,
                    source_scope_ids=[source.scope_id],
                    source_graph_ids=[source.id],
                    source_concept_ids=[source_concept.id],
                    created_at=now,
                    updated_at=now,
                )
                concepts.append(existing)
                by_key[canonical_key] = existing
                changed = True
            else:
                updates: dict[str, Any] = {}
                for field, value in (
                    ("source_scope_ids", source.scope_id),
                    ("source_graph_ids", source.id),
                    ("source_concept_ids", source_concept.id),
                ):
                    values = list(getattr(existing, field))
                    if value not in values:
                        values.append(value)
                        updates[field] = values
                if updates:
                    updates["updated_at"] = utc_now()
                    existing = existing.model_copy(update=updates)
                    concepts[concepts.index(by_key[canonical_key])] = existing
                    by_key[canonical_key] = existing
                    changed = True
            source_to_learner[source_concept.id] = existing.id

        existing_edges = {(edge.source_concept_id, edge.target_concept_id, edge.type): edge for edge in edges}
        for source_edge in source.edges:
            source_id = source_to_learner.get(source_edge.source)
            target_id = source_to_learner.get(source_edge.target)
            if source_id is None or target_id is None:
                continue
            edge_type = _edge_type(source_edge.type)
            key = (source_id, target_id, edge_type)
            existing = existing_edges.get(key)
            if existing is None:
                edge = LearnerGraphEdge(
                    id=f"learner_edge_{uuid4().hex}",
                    source_concept_id=source_id,
                    target_concept_id=target_id,
                    type=edge_type,
                    rationale=source_edge.justification,
                    source_graph_ids=[source.id],
                    status=_edge_status(source_edge.support_status),
                )
                edges.append(edge)
                existing_edges[key] = edge
                changed = True
            elif source.id not in existing.source_graph_ids:
                updated = existing.model_copy(
                    update={
                        "source_graph_ids": [*existing.source_graph_ids, source.id],
                    }
                )
                edges[edges.index(existing)] = updated
                existing_edges[key] = updated
                changed = True

        event = LearnerGraphEvent(
            id=f"learner_event_{uuid4().hex}",
            learner_id=learner_id,
            event_type="topic_graph_imported",
            concept_id=graph.id,
            source_graph_id=source.id,
            metadata={"source_scope_id": source.scope_id, "changed": changed},
            created_at=utc_now(),
        )
        if changed:
            graph = graph.model_copy(
                update={
                    "concepts": concepts,
                    "edges": edges,
                    "revision": graph.revision + 1,
                    "state_version": graph.state_version + 1,
                    "updated_at": utc_now(),
                }
            )
        # The event and projection update commit together so a partial import
        # cannot leave an audit record without the corresponding graph state.
        self._save_event(event, commit=False)
        self._save_graph(graph)
        return LearnerGraphMutationResponse(graph=graph, event=event)

    def append_event(self, learner_id: str, request: LearnerGraphEventCreate) -> LearnerGraphMutationResponse:
        graph = self.get_graph(learner_id)
        concept_index = {concept.id: index for index, concept in enumerate(graph.concepts)}
        index = concept_index.get(request.concept_id)
        if index is None:
            raise KeyError(request.concept_id)

        concept = graph.concepts[index]
        state_map: dict[str, LearnerNodeState] = {
            "concept_explored": "explored",
            "lesson_started": "explored",
            "lesson_completed": "developing",
            "assessment_evidence": "developing",
            "concept_demonstrated": "demonstrated",
            "concept_review_due": "review_due",
            "misconception_detected": "misconception_detected",
        }
        now = utc_now()
        next_state = state_map[request.event_type]
        next_count = concept.evidence_count + (1 if request.event_type in {"lesson_completed", "assessment_evidence", "concept_demonstrated"} else 0)
        updated_concept = concept.model_copy(
            update={
                "state": next_state,
                "evidence_count": next_count,
                "last_evidence_at": now if next_count > concept.evidence_count else concept.last_evidence_at,
                "updated_at": now,
            }
        )
        concepts = list(graph.concepts)
        concepts[index] = updated_concept
        graph = graph.model_copy(
            update={
                "concepts": concepts,
                "revision": graph.revision + 1,
                "state_version": graph.state_version + 1,
                "updated_at": now,
            }
        )
        event = LearnerGraphEvent(
            id=f"learner_event_{uuid4().hex}",
            learner_id=learner_id,
            event_type=request.event_type,
            concept_id=request.concept_id,
            source_graph_id=request.source_graph_id,
            evidence_id=request.evidence_id,
            metadata=request.metadata,
            created_at=now,
        )
        self._save_event(event, commit=False)
        self._save_graph(graph)
        return LearnerGraphMutationResponse(graph=graph, event=event)

    def _save_event(self, event: LearnerGraphEvent, *, commit: bool = True) -> None:
        self.connection.execute(
            "INSERT INTO learner_graph_events(id, learner_id, concept_id, event_type, payload, created_at) VALUES(?, ?, ?, ?, ?, ?)",
            (event.id, event.learner_id, event.concept_id, event.event_type, event.model_dump_json(), event.created_at.isoformat()),
        )
        if commit:
            self.connection.commit()

    def list_events(self, learner_id: str, limit: int = 100) -> list[LearnerGraphEvent]:
        rows = self.connection.execute(
            "SELECT payload FROM learner_graph_events WHERE learner_id = ? ORDER BY rowid DESC LIMIT ?",
            (learner_id, limit),
        ).fetchall()
        return [LearnerGraphEvent.model_validate_json(row["payload"]) for row in rows]


def build_learner_graph_router(store_provider: Any) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["learner-graph"])

    def learner_id_path() -> Any:
        return Path(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.:-]+$")

    @router.get("/learners/{learner_id}/knowledge-graph", response_model=LearnerGraph)
    def get_learner_graph(learner_id: str = learner_id_path()) -> LearnerGraph:
        return LearnerGraphRepository(store_provider()).get_graph(learner_id)

    @router.post(
        "/learners/{learner_id}/knowledge-graph/import",
        response_model=LearnerGraphMutationResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def import_graph(request: LearnerGraphImportRequest, learner_id: str = learner_id_path()) -> LearnerGraphMutationResponse:
        db = store_provider()
        source = db.get_graph(request.graph_id)
        if source is None:
            raise HTTPException(status_code=404, detail={"code": "graph_not_found", "message": "Source graph does not exist."})
        return LearnerGraphRepository(db).import_topic_graph(learner_id, source)

    @router.post(
        "/learners/{learner_id}/knowledge-graph/events",
        response_model=LearnerGraphMutationResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def append_event(request: LearnerGraphEventCreate, learner_id: str = learner_id_path()) -> LearnerGraphMutationResponse:
        try:
            return LearnerGraphRepository(store_provider()).append_event(learner_id, request)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail={"code": "learner_concept_not_found", "message": "Learner graph concept does not exist."}) from exc

    @router.get("/learners/{learner_id}/knowledge-graph/events", response_model=list[LearnerGraphEvent])
    def list_events(learner_id: str = learner_id_path(), limit: int = 100) -> list[LearnerGraphEvent]:
        if limit < 1 or limit > 200:
            raise HTTPException(status_code=422, detail={"code": "invalid_limit", "message": "limit must be between 1 and 200."})
        return LearnerGraphRepository(store_provider()).list_events(learner_id, limit)

    return router
