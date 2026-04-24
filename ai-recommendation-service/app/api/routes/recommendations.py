from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import get_feedback_service, get_recommendation_service
from app.api.security import get_authenticated_user_id, verify_recommendation_caller
from app.schemas import FeedbackBody, RecommendationItem
from app.services.bootstrap import rehydrate_from_user_service
from app.services.feedback_service import FeedbackService
from app.services.recommendation_service import RecommendationService

log = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

router = APIRouter()


@router.get("/recommendations", response_model=list[RecommendationItem])
async def get_recommendations(
    user_id: str = Query(...),
    limit: int = Query(5, ge=1, le=50),
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    svc: RecommendationService = Depends(get_recommendation_service),
):
    verify_recommendation_caller(user_id, creds, x_user_id)
    try:
        recs = await svc.recommend(user_id=user_id, limit=limit)
    except KeyError:
        if await rehydrate_from_user_service():
            try:
                recs = await svc.recommend(user_id=user_id, limit=limit)
            except KeyError:
                raise HTTPException(
                    status_code=404,
                    detail="User not found or not a mentee in match data",
                ) from None
        else:
            raise HTTPException(
                status_code=404,
                detail="User not found or not a mentee in match data",
            ) from None
    return [
        RecommendationItem(
            mentor_id=str(r["mentor_id"]),
            score=float(r["score"]),
            mentor_profile_id=r.get("mentor_profile_id"),
            display_name=r.get("display_name"),
            expertise_areas=r.get("expertise_areas"),
            tier_id=r.get("tier_id"),
            session_credit_cost=r.get("session_credit_cost"),
        )
        for r in recs
    ]


@router.post("/recommendations/feedback")
async def post_feedback(
    body: FeedbackBody,
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    fee: FeedbackService = Depends(get_feedback_service),
) -> dict[str, Any]:
    source = get_authenticated_user_id(creds, x_user_id)
    try:
        return await fee.record(
            source_user_id=source,
            target_user_id=body.target_user_id,
            interaction_type=body.interaction_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
