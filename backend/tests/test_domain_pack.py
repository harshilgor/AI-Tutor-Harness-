from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.domain_pack import NEURAL_NETWORK_FOUNDATIONS, get_pack, graph_for_pack, validate_pack
from backend.app.models import utc_now
from backend.app.models import TopicScope
from backend.app.session_models import LearningSession
from backend.app.storage import Store


def test_domain_pack_rejects_invalid_source_concept_and_skill_references():
    bad_source = deepcopy(NEURAL_NETWORK_FOUNDATIONS)
    bad_source["concepts"][0]["sourceIds"] = ["missing"]
    with pytest.raises(ValueError, match="unknown source"):
        validate_pack(bad_source)
    bad_concept = deepcopy(NEURAL_NETWORK_FOUNDATIONS)
    bad_concept["assessmentBlueprints"][0]["conceptId"] = "missing"
    with pytest.raises(ValueError, match="unknown concept"):
        validate_pack(bad_concept)
    bad_skill = deepcopy(NEURAL_NETWORK_FOUNDATIONS)
    del bad_skill["assessmentBlueprints"][0]["skill"]
    with pytest.raises(ValueError, match="requires a skill"):
        validate_pack(bad_skill)


def test_existing_session_remains_pinned_when_pack_definition_changes():
    path = Path.cwd() / "backend" / "data" / f"domain-pack-{uuid4().hex}.db"
    store = Store(path)
    try:
        pack = get_pack("neural-network-foundations", 1)
        graph = graph_for_pack(pack)
        store.save_scope(TopicScope(id=graph.scope_id, topic=pack["title"], resolved_meaning=pack["title"], objective="Learn", depth="introductory", created_at=utc_now()))
        store.save_graph(graph)
        session = LearningSession(id="session-pack", learner_id="local", graph_id=graph.id, graph_revision=graph.version, domain_pack_id=pack["id"], domain_pack_version=pack["version"], created_at=utc_now(), updated_at=utc_now())
        store.save_session(session)
        changed = deepcopy(pack)
        changed["version"] = 2
        changed["title"] = "Changed title"
        changed_graph = graph_for_pack(changed)
        store.save_scope(TopicScope(id=changed_graph.scope_id, topic=changed["title"], resolved_meaning=changed["title"], objective="Learn", depth="introductory", created_at=utc_now()))
        store.save_graph(changed_graph)
        restored = store.get_session(session.id)
        assert restored and restored.domain_pack_id == "neural-network-foundations"
        assert restored.domain_pack_version == 1 and restored.graph_id == graph.id
    finally:
        store.close()
        path.unlink(missing_ok=True)
