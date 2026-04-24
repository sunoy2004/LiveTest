from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.match_interactions import MatchInteractionRepository
from app.services import recommendation_cache

_VALID = frozenset({"REJECTED_SUGGESTION", "SUCCESSFUL_MENTORSHIP"})


class FeedbackService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MatchInteractionRepository(session)

    def validate_type(self, interaction_type: str) -> None:
        if interaction_type not in _VALID:
            raise ValueError("invalid interaction_type")

    async def record(
        self,
        *,
        source_user_id: str,
        target_user_id: str,
        interaction_type: str,
    ) -> dict[str, Any]:
        self.validate_type(interaction_type)
        await self._repo.upsert_feedback(
            source_user_id=uuid.UUID(source_user_id),
            target_user_id=uuid.UUID(target_user_id),
            interaction_type=interaction_type,
        )
        await recommendation_cache.invalidate_user(source_user_id)
        return {
            "ok": True,
            "source_user_id": source_user_id,
            "target_user_id": target_user_id,
            "interaction_type": interaction_type,
            "weight": self._repo.weight_for(interaction_type),
        }
