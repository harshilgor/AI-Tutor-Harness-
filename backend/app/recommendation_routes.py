"""Owner-scoped API for transparent next-action recommendations."""
from fastapi import APIRouter, Depends, Header
from .material_routes import material_owner
from .recommendation_models import RecommendationInteractionCreate
from .recommendation_service import RecommendationService


def build_recommendation_router(store_provider):
    router = APIRouter(prefix="/v1")

    @router.get("/sessions/{sid}/recommendations")
    def recommendations(sid: str, owner=Depends(material_owner), db=Depends(store_provider)):
        return RecommendationService(db).get_or_create(owner, sid)

    @router.post("/recommendations/{recommendation_id}/interactions", status_code=204)
    def interaction(recommendation_id: str, command: RecommendationInteractionCreate,
                    owner=Depends(material_owner), db=Depends(store_provider),
                    key: str | None = Header(default=None, alias="Idempotency-Key", max_length=200)):
        RecommendationService(db).record_interaction(
            owner,
            recommendation_id,
            command.event_type,
            command.reason,
            key,
            command.evidence_id,
        )

    return router
