from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db import get_session_factory
from app.services.feedback_service import FeedbackService
from app.services.recommendation_service import RecommendationService


async def get_db_session() -> AsyncIterator[AsyncSession]:
    fac = get_session_factory()
    async with fac() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_recommendation_service(
    session: AsyncSession = Depends(get_db_session),
) -> RecommendationService:
    return RecommendationService(session)


def get_feedback_service(
    session: AsyncSession = Depends(get_db_session),
) -> FeedbackService:
    return FeedbackService(session)
