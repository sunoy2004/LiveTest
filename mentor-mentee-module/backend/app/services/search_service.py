import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MenteeProfile, MentorProfile
from app.schemas.search import SearchResult, SearchRole


class SearchService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(
        self,
        q: str,
        role: SearchRole = SearchRole.mentor,
        limit: int = 10,
    ) -> list[SearchResult]:
        query = (q or "").strip().lower()
        if not query:
            return []

        limit = max(1, min(int(limit), 50))

        user_id = self._try_parse_uuid(query)
        results: list[SearchResult] = []

        if role in (SearchRole.mentor, SearchRole.all):
            results.extend(await self._search_mentors(query=query, user_id=user_id, limit=limit))
            if role != SearchRole.all and len(results) >= limit:
                return results[:limit]

        if role in (SearchRole.mentee, SearchRole.all):
            remaining = limit - len(results)
            if remaining > 0:
                results.extend(await self._search_mentees(query=query, user_id=user_id, limit=remaining))

        return results[:limit]

    @staticmethod
    def _try_parse_uuid(value: str) -> uuid.UUID | None:
        try:
            return uuid.UUID(value)
        except ValueError:
            return None

    async def _search_mentors(
        self,
        *,
        query: str,
        user_id: uuid.UUID | None,
        limit: int,
    ) -> list[SearchResult]:
        stmt = select(MentorProfile).limit(limit)

        if user_id is not None:
            stmt = stmt.where(MentorProfile.user_id == user_id)
        else:
            name_match = MentorProfile.full_name.ilike(f"%{query}%")
            expertise_match = MentorProfile.expertise_areas.contains([query])
            stmt = stmt.where(or_(name_match, expertise_match))

        mentors = (await self._session.scalars(stmt)).all()
        return [
            SearchResult(
                user_id=m.user_id,
                full_name=m.full_name,
                role=SearchRole.mentor,
                expertise=list(m.expertise_areas or []),
                tier=m.tier_id,
            )
            for m in mentors
        ]

    async def _search_mentees(
        self,
        *,
        query: str,
        user_id: uuid.UUID | None,
        limit: int,
    ) -> list[SearchResult]:
        stmt = select(MenteeProfile).limit(limit)

        if user_id is not None:
            stmt = stmt.where(MenteeProfile.user_id == user_id)
        else:
            name_match = MenteeProfile.full_name.ilike(f"%{query}%")
            goals_match = MenteeProfile.learning_goals.contains([query])
            stmt = stmt.where(or_(name_match, goals_match))

        mentees = (await self._session.scalars(stmt)).all()
        return [
            SearchResult(
                user_id=m.user_id,
                full_name=m.full_name,
                role=SearchRole.mentee,
                expertise=list(m.learning_goals or []),
                tier=None,
            )
            for m in mentees
        ]

