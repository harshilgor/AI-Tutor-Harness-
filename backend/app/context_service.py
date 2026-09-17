"""Bounded authorized retrieval and canonical learner evidence."""
import re
import hashlib
import json
from sqlalchemy import text
from .material_service import MaterialService, uid, encoded, problem
from .policy_models import LearnerEvidenceProjection, ConceptEvidence
from .state_service import LearnerStateService


def canonical_evidence(store, owner, graph):
    states = [s for s in LearnerStateService(store).get_state(owner).states if s.graph_id == graph.id and s.graph_version == graph.version]
    by_id = {s.concept_id: s for s in states}
    concepts = []
    for concept in graph.concepts:
        state = by_id.get(concept.id)
        status = state.status.value if state else "unexplored"
        concepts.append(ConceptEvidence(concept_id=concept.id, state="explored" if status == "exposed" else status,
            evidence_count=int(bool(state and state.last_evidence_id)), demonstrated=status == "demonstrated",
            evidence_ids=[state.last_evidence_id] if state and state.last_evidence_id else []))
    return LearnerEvidenceProjection(learner_id=owner, state_version=max((s.version for s in states), default=0), concepts=concepts)


def retrieve(store, owner, sid, query, byte_budget=16000, selected_span_ids=None):
    """Resolve attached passages with an optional explicit selection boundary."""
    service = MaterialService(store)
    selected_span_ids = list(selected_span_ids or [])
    if len(set(selected_span_ids)) != len(selected_span_ids):
        problem("duplicate_source_selection", "A passage may be selected only once.")
    attached = set(service.attachments(owner, sid))
    if selected_span_ids:
        selected = []
        for span_id in selected_span_ids:
            block = service.source(owner, span_id)
            if block["versionId"] not in attached:
                problem("source_not_attached", "Select passages only from material attached to this conversation.", 409)
            version = service.version(owner, block["versionId"])
            if version["role"] in {"answer_key", "sample_paper"} or version["status"] not in {"ready", "partially_ready"} or block["kind"] == "private_solution":
                problem("source_unavailable", "That passage cannot support teaching or assessment.", 409)
            selected.append({"spanId": block["id"], "versionId": block["versionId"], "pageIndex": block["pageIndex"], "title": version["title"], "text": block["text"]})
        if sum(len(item["text"].encode("utf-8")) for item in selected) > byte_budget:
            problem("source_budget_exceeded", "Selected passages exceed the context budget. Choose fewer passages.")
        return selected
    terms = set(re.findall(r"\w{3,}", query.lower()))
    candidates = []
    for vid in attached:
        version = service.version(owner, vid)
        if version["role"] in {"answer_key", "sample_paper"} or version["status"] not in {"ready", "partially_ready"}:
            continue
        for block in service.blocks(owner, vid):
            score = len(terms & set(re.findall(r"\w{3,}", block["text"].lower())))
            if score and block["kind"] != "private_solution":
                candidates.append((score, block, version["title"]))
    candidates.sort(key=lambda item: (-item[0], item[1]["id"]))
    selected, used = [], 0
    for score, block, title in candidates:
        cost = len(block["text"].encode("utf-8")) + len(title.encode("utf-8")) + 200
        if used + cost > byte_budget:
            continue
        selected.append({"spanId": block["id"], "versionId": block["versionId"], "pageIndex": block["pageIndex"], "title": title, "text": block["text"]})
        used += cost
        if len(selected) == 6:
            break
    return selected


def save_manifest(store, owner, sid, query, sources, selected_span_ids=None):
    manifest = {
        "id": uid("context"), "sessionId": sid, "schemaVersion": 1,
        "retrievalMode": "explicit_selection" if selected_span_ids else "lexical_overlap", "evidenceByteBudget": 16000,
        "queryHash": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "sources": [{key: source[key] for key in ("spanId", "versionId", "pageIndex")} for source in sources],
        "evidenceBytes": sum(len(source["text"].encode("utf-8")) for source in sources),
        "selectedSpanIds": list(selected_span_ids or []),
        "limitations": ["Text extraction only", "No claim-level verification", "No semantic ranking", "Only attached, learner-owned passages enter this context", "Sample papers and answer keys excluded"],
    }
    with store.transaction() as connection:
        connection.execute(text("INSERT INTO context_records(id,owner_id,kind,session_id,sequence,payload) VALUES(:id,:owner,'retrieval_manifest',:sid,0,:payload)"), {"id": manifest["id"], "owner": owner, "sid": sid, "payload": encoded(manifest)})
    return manifest


def get_manifest(store, owner, manifest_id):
    with store.engine.connect() as connection:
        row = connection.execute(text("SELECT payload FROM context_records WHERE id=:id AND owner_id=:owner AND kind='retrieval_manifest'"), {"id": manifest_id, "owner": owner}).first()
    if row is None:
        problem("context_not_found", "Context is not available", 404)
    manifest = json.loads(row[0])
    service = MaterialService(store)
    service.session(owner, manifest["sessionId"])
    for source in manifest["sources"]:
        service.version(owner, source["versionId"])
    return manifest
