"""Tests for Course Roadmap Progression & Adaptive Milestones (Phase 3)."""

from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import text

try:
    from backend.app.main import app, get_store
except ModuleNotFoundError:
    from app.main import app, get_store


client = TestClient(app)

ALICE = {"X-Dev-Learner-Id": "roadmap_alice"}


def _create_course(name="Advanced Distributed Systems", goal="Consensus, Paxos, and Raft", headers=ALICE):
    response = client.post(
        "/v1/courses",
        json={"name": name, "goal": goal},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _cleanup_course(course_id, headers=ALICE):
    client.delete(f"/v1/courses/{course_id}", headers=headers)


def test_generate_tailored_roadmap():
    course = _create_course(name="Build an OS", goal="Write a kernel in C and Rust")
    try:
        # Generate tailored roadmap with project emphasis
        res = client.post(
            f"/v1/courses/{course['id']}/roadmap/generate",
            json={"prompt": "Hands-on project building a bootloader and memory manager", "replace_existing": True},
            headers=ALICE,
        )
        assert res.status_code == 200, res.text
        nodes = res.json()
        assert len(nodes) >= 4
        # Verify phases reflect project focus
        phases = [n["phase"] for n in nodes]
        assert any("Implementation" in p or "Setup" in p or "Capstone" in p for p in phases)
        # Verify concept IDs are populated
        assert all(n.get("conceptId") is not None for n in nodes)
        # Verify sequential order_index
        order_indices = [n["orderIndex"] for n in nodes]
        assert order_indices == list(range(len(nodes)))
    finally:
        _cleanup_course(course["id"])


def test_roadmap_nodes_crud_and_reorder():
    course = _create_course(name="Database Internals", goal="LSM Trees and B-Trees")
    try:
        # 1. Add node
        add_res = client.post(
            f"/v1/courses/{course['id']}/roadmap/nodes",
            json={"title": "Write-Ahead Logging (WAL) internals", "phase": "Storage Engines"},
            headers=ALICE,
        )
        assert add_res.status_code == 201, add_res.text
        new_node = add_res.json()
        assert new_node["title"] == "Write-Ahead Logging (WAL) internals"
        assert new_node["phase"] == "Storage Engines"
        assert new_node["status"] == "planned"
        assert new_node.get("conceptId") is not None

        # 2. Update node status and title
        node_id = new_node["id"]
        update_res = client.patch(
            f"/v1/courses/{course['id']}/roadmap/nodes/{node_id}",
            json={"status": "in_progress", "title": "WAL Crash Recovery Protocol"},
            headers=ALICE,
        )
        assert update_res.status_code == 200, update_res.text
        updated_node = update_res.json()
        assert updated_node["status"] == "in_progress"
        assert updated_node["title"] == "WAL Crash Recovery Protocol"

        # 3. Reorder nodes
        roadmap_res = client.get(f"/v1/courses/{course['id']}/roadmap", headers=ALICE)
        current_nodes = roadmap_res.json()
        node_ids = [n["id"] for n in current_nodes]
        reversed_ids = list(reversed(node_ids))

        reorder_res = client.post(
            f"/v1/courses/{course['id']}/roadmap/reorder",
            json={"node_ids": reversed_ids},
            headers=ALICE,
        )
        assert reorder_res.status_code == 200, reorder_res.text
        reordered_nodes = reorder_res.json()
        assert [n["id"] for n in reordered_nodes] == reversed_ids
        assert [n["orderIndex"] for n in reordered_nodes] == list(range(len(reversed_ids)))

        # 4. Delete node
        del_res = client.delete(f"/v1/courses/{course['id']}/roadmap/nodes/{node_id}", headers=ALICE)
        assert del_res.status_code == 204

        # Verify deletion
        refreshed_res = client.get(f"/v1/courses/{course['id']}/roadmap", headers=ALICE)
        refreshed_ids = [n["id"] for n in refreshed_res.json()]
        assert node_id not in refreshed_ids
    finally:
        _cleanup_course(course["id"])


def test_evaluate_roadmap_progression():
    course = _create_course(name="Machine Learning Foundations", goal="Linear regression to neural networks")
    try:
        nodes = course["roadmap"]
        assert len(nodes) >= 3
        node_1 = nodes[0]
        node_2 = nodes[1]
        node_3 = nodes[2]

        cid_1 = node_1.get("conceptId") or node_1.get("concept_id")
        cid_2 = node_2.get("conceptId") or node_2.get("concept_id")
        cid_3 = node_3.get("conceptId") or node_3.get("concept_id")

        now = datetime.now(timezone.utc)
        db = get_store()

        with db.transaction() as conn:
            # Ensure learner exists
            conn.execute(
                text(
                    "INSERT OR IGNORE INTO learners(id, identity_kind, display_name, created_at, updated_at) "
                    "VALUES('roadmap_alice', 'dev', 'Alice', :now, :now)"
                ),
                {"now": now},
            )
            # Ensure graph version exists for foreign keys if required
            conn.execute(
                text("INSERT OR IGNORE INTO topic_scopes(id, payload) VALUES('scope_test', '{}')")
            )
            conn.execute(
                text("INSERT OR IGNORE INTO graph_versions(id, scope_id, payload) VALUES('graph_test', 'scope_test', '{}')")
            )

            # Node 1: concept demonstrated in learner_concept_states -> should become completed
            conn.execute(
                text(
                    "INSERT OR REPLACE INTO learner_concept_states("
                    "learner_id, concept_id, graph_id, graph_version, status, confidence, uncertainty, "
                    "version, policy_version, provenance_json, created_at, updated_at) "
                    "VALUES('roadmap_alice', :cid, 'graph_test', 1, 'demonstrated', 0.9, 0.1, 1, 'v1', '{}', :now, :now)"
                ),
                {"cid": cid_1, "now": now},
            )

            # Node 2: concept developing -> should become in_progress
            conn.execute(
                text(
                    "INSERT OR REPLACE INTO learner_concept_states("
                    "learner_id, concept_id, graph_id, graph_version, status, confidence, uncertainty, "
                    "version, policy_version, provenance_json, created_at, updated_at) "
                    "VALUES('roadmap_alice', :cid, 'graph_test', 1, 'developing', 0.5, 0.3, 1, 'v1', '{}', :now, :now)"
                ),
                {"cid": cid_2, "now": now},
            )

            # Node 3: concept memory indicates needs_remediation -> should become needs_review
            conn.execute(
                text(
                    "INSERT OR REPLACE INTO concept_memory_states("
                    "learner_id, concept_id, graph_id, graph_version, first_learned_at, next_review_at, "
                    "review_count, mastery_estimate, needs_remediation, created_at, updated_at) "
                    "VALUES('roadmap_alice', :cid, 'graph_test', 1, :now, :now, 2, 'needs_reinforcement', 1, :now, :now)"
                ),
                {"cid": cid_3, "now": now},
            )

        # Evaluate progression
        eval_res = client.post(f"/v1/courses/{course['id']}/roadmap/evaluate", headers=ALICE)
        assert eval_res.status_code == 200, eval_res.text
        result = eval_res.json()

        assert result["nodesUpdated"] >= 2
        node_map = {n["id"]: n for n in result["roadmap"]}

        assert node_map[node_1["id"]]["status"] == "completed"
        assert node_map[node_2["id"]]["status"] == "in_progress"
        assert node_map[node_3["id"]]["status"] == "needs_review"

        # Check that due_review_count detects the concept due for review
        assert result["dueReviewCount"] >= 1

        # Check course summary reflection
        course_res = client.get(f"/v1/courses/{course['id']}", headers=ALICE)
        assert course_res.status_code == 200
        course_data = course_res.json()
        assert course_data["summary"]["dueReviewCount"] >= 1
        assert course_data["summary"]["roadmapProgress"] > 0
    finally:
        _cleanup_course(course["id"])
