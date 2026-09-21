"""Study-note and synthesis-proposal endpoints."""

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query

from .learning_routes import run_job
from .material_routes import material_owner
from .material_service import MaterialService
from .study_note_models import InsightInput, ProposalAcceptInput, ProposalCreate, StudySettingsInput
from .study_note_service import StudyNoteService
from .workflow_store import WorkflowStore


def build_study_note_router(store_provider, provider_getter):
    router = APIRouter(prefix="/v1")

    def service(db=Depends(store_provider)):
        return StudyNoteService(db, provider_getter())

    def enqueue(tasks, db, owner, target, kind, payload, key):
        job = WorkflowStore(db).enqueue(owner, target, kind, payload, key)
        tasks.add_task(run_job, db, provider_getter(), job["id"])
        return job

    @router.get("/sessions/{sid}/study-note")
    def find_study_note(sid: str, owner=Depends(material_owner), svc=Depends(service)):
        MaterialService(svc.store).session(owner, sid)
        note = svc.find_note(owner, sid)
        if note is None:
            from .material_service import problem
            problem("study_note_missing", "This chat has no study note yet.", 404)
        return {
            "noteId": note.id,
            "title": note.title,
            "revision": note.revision,
            "tutorUpdates": svc.tutor_updates_mode(note),
            "sessionIds": (note.frontmatter or {}).get("session_ids", []),
            "sections": svc.list_sections(owner, note.id),
        }

    @router.post("/sessions/{sid}/study-note", status_code=201)
    def create_study_note(sid: str, owner=Depends(material_owner), svc=Depends(service)):
        MaterialService(svc.store).session(owner, sid)
        note = svc.get_or_create_note(owner, sid)
        return {
            "noteId": note.id,
            "title": note.title,
            "revision": note.revision,
            "tutorUpdates": svc.tutor_updates_mode(note),
            "sessionIds": (note.frontmatter or {}).get("session_ids", []),
            "sections": svc.list_sections(owner, note.id),
        }

    @router.patch("/study-notes/{note_id}/settings")
    def study_settings(note_id: str, request: StudySettingsInput, owner=Depends(material_owner), svc=Depends(service)):
        note = svc.set_tutor_updates(owner, note_id, request.tutor_updates, request.expected_revision)
        return {"noteId": note.id, "revision": note.revision, "tutorUpdates": svc.tutor_updates_mode(note)}

    @router.post("/sessions/{sid}/study-note/insights", status_code=201)
    def save_insight(sid: str, request: InsightInput, owner=Depends(material_owner), svc=Depends(service)):
        MaterialService(svc.store).session(owner, sid)
        return svc.save_insight(owner, sid, request.heading, request.body)

    @router.post("/sessions/{sid}/note-proposals", status_code=202)
    def propose(sid: str, command: ProposalCreate, tasks: BackgroundTasks, owner=Depends(material_owner),
                db=Depends(store_provider), key: str = Header(alias="Idempotency-Key", min_length=1, max_length=200)):
        MaterialService(db).session(owner, sid)
        return enqueue(tasks, db, owner, sid, "note_synthesis", command.model_dump(mode="json"), key)

    @router.get("/sessions/{sid}/note-proposals")
    def list_proposals(sid: str, status: str | None = Query(default=None, max_length=20),
                       owner=Depends(material_owner), svc=Depends(service)):
        MaterialService(svc.store).session(owner, sid)
        return {"proposals": svc.list_proposals(owner, sid, status)}

    @router.get("/note-proposals/{proposal_id}")
    def get_proposal(proposal_id: str, owner=Depends(material_owner), svc=Depends(service)):
        record = svc.get_proposal(owner, proposal_id)
        session = MaterialService(svc.store).session(owner, record["session_id"])
        return {**record, "sessionTitle": session.title or session.goal, "noteTitle": svc.notes.get(owner, record["note_id"]).title}

    @router.post("/note-proposals/{proposal_id}/accept")
    def accept_proposal(proposal_id: str, request: ProposalAcceptInput, owner=Depends(material_owner), svc=Depends(service)):
        return svc.accept(owner, proposal_id, request.body, request.heading, request.expected_revision)

    @router.post("/note-proposals/{proposal_id}/reject")
    def reject_proposal(proposal_id: str, owner=Depends(material_owner), svc=Depends(service)):
        return svc.reject(owner, proposal_id)

    return router
