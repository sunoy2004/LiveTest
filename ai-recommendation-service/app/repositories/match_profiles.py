from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.vector_utils import to_pgvector_literal


class MatchProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        *,
        user_id: uuid.UUID,
        role: str,
        is_active: bool,
        combined_text_payload: str,
        embedding: list[float],
    ) -> None:
        vec = to_pgvector_literal(embedding)
        await self._session.execute(
            text(
                """
                INSERT INTO match_profiles
                  (user_id, role, is_active, combined_text_payload, embedding, updated_at)
                VALUES
                  (:user_id, :role, :is_active, :text, CAST(:vec AS vector), now())
                ON CONFLICT (user_id) DO UPDATE SET
                  role = EXCLUDED.role,
                  is_active = EXCLUDED.is_active,
                  combined_text_payload = EXCLUDED.combined_text_payload,
                  embedding = EXCLUDED.embedding,
                  updated_at = now()
                """
            ),
            {
                "user_id": user_id,
                "role": role,
                "is_active": is_active,
                "text": combined_text_payload,
                "vec": vec,
            },
        )

    async def source_row_exists_for_mentee(
        self,
        *,
        user_id: uuid.UUID,
    ) -> bool:
        r = await self._session.execute(
            text(
                """
                SELECT 1 FROM match_profiles
                WHERE user_id = :user_id
                  AND role IN ('MENTEE', 'BOTH')
                """
            ),
            {"user_id": user_id},
        )
        return r.first() is not None

    async def recommend(
        self,
        *,
        user_id: uuid.UUID,
        limit: int,
        hybrid: bool,
    ) -> list[dict[str, Any]]:
        """Return rows with keys mentor_id (UUID str), score (0..1 float), optional final_rank for debug."""
        if hybrid:
            return await self._recommend_hybrid(user_id=user_id, limit=limit)
        return await self._recommend_semantic_only(user_id=user_id, limit=limit)

    async def _recommend_semantic_only(
        self, *, user_id: uuid.UUID, limit: int
    ) -> list[dict[str, Any]]:
        r = await self._session.execute(
            text(
                """
                SELECT
                  target.user_id::text AS mentor_id,
                  (1.0 - (target.embedding <=> source.embedding))::float AS score
                FROM match_profiles target
                JOIN match_profiles source ON source.user_id = :user_id
                WHERE source.role IN ('MENTEE', 'BOTH')
                  AND target.role IN ('MENTOR', 'BOTH')
                  AND target.is_active = TRUE
                  AND target.user_id != :user_id
                  AND target.user_id NOT IN (
                    SELECT target_user_id
                    FROM match_interactions
                    WHERE source_user_id = :user_id
                      AND interaction_type = 'REJECTED_SUGGESTION'
                  )
                ORDER BY target.embedding <=> source.embedding
                LIMIT :limit
                """
            ),
            {"user_id": user_id, "limit": limit},
        )
        return [
            {
                "mentor_id": row[0],
                "score": float(row[1]),
            }
            for row in r.fetchall()
        ]

    async def _recommend_hybrid(self, *, user_id: uuid.UUID, limit: int) -> list[dict[str, Any]]:
        r = await self._session.execute(
            text(
                """
                WITH w AS (
                  SELECT target_user_id,
                         COALESCE(SUM(weight), 0) AS wsum
                  FROM match_interactions
                  WHERE source_user_id = :user_id
                  GROUP BY target_user_id
                )
                SELECT
                  target.user_id::text AS mentor_id,
                  (1.0 - (target.embedding <=> source.embedding))::float AS score,
                  (
                    100.0 * (1.0 - (target.embedding <=> source.embedding))::float
                    + COALESCE(w.wsum, 0.0)
                  )::float AS final_rank
                FROM match_profiles target
                JOIN match_profiles source ON source.user_id = :user_id
                LEFT JOIN w ON w.target_user_id = target.user_id
                WHERE source.role IN ('MENTEE', 'BOTH')
                  AND target.role IN ('MENTOR', 'BOTH')
                  AND target.is_active = TRUE
                  AND target.user_id != :user_id
                  AND target.user_id NOT IN (
                    SELECT target_user_id
                    FROM match_interactions
                    WHERE source_user_id = :user_id
                      AND interaction_type = 'REJECTED_SUGGESTION'
                  )
                ORDER BY final_rank DESC, target.embedding <=> source.embedding
                LIMIT :limit
                """
            ),
            {"user_id": user_id, "limit": limit},
        )
        return [
            {
                "mentor_id": row[0],
                "score": float(row[1]),
            }
            for row in r.fetchall()
        ]
