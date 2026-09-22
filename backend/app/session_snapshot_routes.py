"""Owner-scoped server-authoritative session snapshot API."""

from fastapi import APIRouter, Depends

from .material_routes import material_owner
from .session_models import SessionPositionUpdate, SessionSnapshot
from .session_snapshot_service import SessionSnapshotService


def build_session_snapshot_router(store_provider):
    router = APIRouter(prefix="/v1", tags=["session-snapshot"])

    @router.get("/sessions/{session_id}/snapshot", response_model=SessionSnapshot)
    def snapshot(
        session_id: str,
        owner: str = Depends(material_owner),
        db=Depends(store_provider),
    ) -> SessionSnapshot:
        return SessionSnapshotService(db).get(owner, session_id)

    @router.patch("/sessions/{session_id}/position", response_model=SessionSnapshot)
    def update_position(
        command: SessionPositionUpdate,
        session_id: str,
        owner: str = Depends(material_owner),
        db=Depends(store_provider),
    ) -> SessionSnapshot:
        return SessionSnapshotService(db).update(owner, session_id, command)

    return router
