from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_WEIGHTS: dict[str, int] = {
    "REJECTED_SUGGESTION": -100,
    "SUCCESSFUL_MENTORSHIP": 50,
}


class MatchInteractionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def weight_for(self, interaction_type: str) -> int:
        if interaction_type not in _WEIGHTS:
            raise KeyError("invalid interaction_type")
        return _WEIGHTS[interaction_type]

    async def upsert_feedback(
        self,
        *,
        source_user_id: uuid.UUID,
        target_user_id: uuid.UUID,
        interaction_type: str,
    ) -> None:
        w = self.weight_for(interaction_type)
        iid = uuid.uuid4()
        await self._session.execute(
            text(
                """
                INSERT INTO match_interactions
                  (interaction_id, source_user_id, target_user_id, interaction_type, weight, created_at)
                VALUES
                  (:iid, :s, :t, :typ, :w, now())
                ON CONFLICT (source_user_id, target_user_id, interaction_type) DO UPDATE SET
                  weight = EXCLUDED.weight,
                  created_at = now()
                """
            ),
            {
                "iid": iid,
                "s": source_user_id,
                "t": target_user_id,
                "typ": interaction_type,
                "w": w,
            },
        )

    async def insert_successful_mentorship(
        self,
        *,
        source_user_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> None:
        """Idempotent: same (source, target, SUCCESS) updates timestamp + weight."""
        await self.upsert_feedback(
            source_user_id=source_user_id,
            target_user_id=target_user_id,
            interaction_type="SUCCESSFUL_MENTORSHIP",
        )
