"""Tests for Course Materials & Reference Library (Phase 4)."""

import time
from fastapi.testclient import TestClient
from sqlalchemy import text

try:
    from backend.app.main import app, get_store
    from backend.app.material_service import MaterialService
    from backend.app.context_service import retrieve
except ModuleNotFoundError:
    from app.main import app, get_store
    from app.material_service import MaterialService
    from app.context_service import retrieve


client = TestClient(app)

ALICE = {"X-Dev-Learner-Id": "materials_alice"}
BOB = {"X-Dev-Learner-Id": "materials_bob"}


def _create_course(name="Operating Systems", goal="Virtual memory and page tables", headers=ALICE):
    response = client.post(
        "/v1/courses",
        json={"name": name, "goal": goal},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _cleanup_course(course_id, headers=ALICE):
    client.delete(f"/v1/courses/{course_id}", headers=headers)


def test_course_materials_end_to_end():
    course = _create_course()
    try:
        # 1. Add text material directly to the course
        text_payload = {
            "title": "OSTEP Chapter 18: Virtual Memory & Paging",
            "text": (
                "Paging divides address spaces into fixed-size units called pages. "
                "The operating system translates virtual page numbers (VPN) to physical frame numbers (PFN) "
                "using a per-process page table stored in memory. The TLB acts as a hardware cache for address translations."
            ),
            "role": "textbook",
        }
        add_res = client.post(
            f"/v1/courses/{course['id']}/materials/text",
            json=text_payload,
            headers=ALICE,
        )
        assert add_res.status_code == 201, add_res.text
        material = add_res.json()
        assert material["title"] == text_payload["title"]
        assert material["courseId"] == course["id"]
        assert material["role"] == "textbook"

        # Wait briefly for synchronous or worker ingestion
        store = get_store()
        mat_svc = MaterialService(store)
        mat_svc.process_one()

        # 2. Verify GET /courses/{course_id}/materials
        list_res = client.get(f"/v1/courses/{course['id']}/materials", headers=ALICE)
        assert list_res.status_code == 200, list_res.text
        materials_data = list_res.json()
        assert materials_data["total"] == 1
        assert materials_data["materials"][0]["id"] == material["id"]
        assert materials_data["materials"][0]["courseId"] == course["id"]

        # 3. Verify get_course reports material_count = 1
        course_res = client.get(f"/v1/courses/{course['id']}", headers=ALICE)
        assert course_res.status_code == 200
        assert course_res.json()["summary"]["materialCount"] == 1

        # 4. Create a session linked to the course
        sess_res = client.post(
            "/v1/sessions",
            json={"topic": "How does TLB work?", "courseId": course["id"]},
            headers=ALICE,
        )
        assert sess_res.status_code == 201, sess_res.text
        session = sess_res.json()

        # 5. Verify MaterialService.attachments automatically includes course materials
        attachments = mat_svc.attachments("materials_alice", session["id"])
        assert material["versionId"] in attachments

        # 6. Verify context_service.retrieve retrieves passages from course materials
        passages = retrieve(store, "materials_alice", session["id"], "virtual page numbers and TLB")
        assert len(passages) >= 1
        assert any("virtual page numbers" in p["text"].lower() or "tlb" in p["text"].lower() for p in passages)

        # 7. Detach material from course
        detach_res = client.delete(f"/v1/courses/{course['id']}/materials/{material['id']}", headers=ALICE)
        assert detach_res.status_code == 200, detach_res.text

        # Verify material_count is now 0
        refreshed_course = client.get(f"/v1/courses/{course['id']}", headers=ALICE).json()
        assert refreshed_course["summary"]["materialCount"] == 0

        # 8. Attach material back to course
        attach_res = client.post(f"/v1/courses/{course['id']}/materials/{material['id']}/attach", headers=ALICE)
        assert attach_res.status_code == 200, attach_res.text
        refreshed_course2 = client.get(f"/v1/courses/{course['id']}", headers=ALICE).json()
        assert refreshed_course2["summary"]["materialCount"] == 1

        # 9. Isolation check: Bob cannot access Alice's course materials
        bob_res = client.get(f"/v1/courses/{course['id']}/materials", headers=BOB)
        assert bob_res.status_code == 404
    finally:
        _cleanup_course(course["id"])
