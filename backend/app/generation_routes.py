"""SSE observation endpoints for the shared Ask/Learn generation manager."""
from __future__ import annotations

import json
from fastapi import APIRouter, Depends, Header, Response
from fastapi.responses import StreamingResponse

from .generation_models import GenerationRequest
from .generation_service import GenerationManager
from .generation_store import GenerationStore
from .material_routes import material_owner

SSE_HEADERS = {"Cache-Control": "no-cache, no-transform", "Connection": "keep-alive", "X-Accel-Buffering": "no"}


def _frame(event) -> str:
    return f"id: {event.sequence}\nevent: {event.type}\ndata: {json.dumps(event.model_dump(mode='json', by_alias=True), ensure_ascii=False)}\n\n"


def build_generation_router(store_provider, provider_getter):
    router = APIRouter(prefix="/v1")
    manager = GenerationManager(store_provider(), provider_getter())
    GenerationStore(store_provider()).interrupt_active()

    @router.post("/sessions/{sid}/generations", status_code=202)
    async def create(sid: str, command: GenerationRequest, key: str = Header(alias="Idempotency-Key", min_length=1, max_length=200), owner=Depends(material_owner)):
        record = manager.create(owner, sid, command, key)
        return GenerationStore.descriptor(record)

    @router.get("/generations/{generation_id}")
    def get(generation_id: str, owner=Depends(material_owner)):
        return GenerationStore.descriptor(manager.records.get(owner, generation_id))

    @router.get("/generations/{generation_id}/events")
    async def events(generation_id: str, after: int = 0, last_event_id: str | None = Header(default=None, alias="Last-Event-ID"), owner=Depends(material_owner)):
        if last_event_id and last_event_id.isdigit():
            after = max(after, int(last_event_id))
        async def stream():
            async for event in manager.events(owner, generation_id, after):
                if event.data.get("heartbeat"):
                    yield ": heartbeat\n\n"
                else:
                    yield _frame(event)
        return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)

    @router.post("/generations/{generation_id}/cancel", status_code=202)
    def cancel(generation_id: str, owner=Depends(material_owner)):
        return GenerationStore.descriptor(manager.cancel(owner, generation_id))

    return router
