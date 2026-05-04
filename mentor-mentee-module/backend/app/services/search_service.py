import uuid

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MenteeProfile, MentorProfile
from app.schemas.search import SearchResult, SearchRole
from app.utils.display_name import label_from_user_id


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
        limit = max(1, min(int(limit), 50))

        results: list[SearchResult] = []
        user_id = self._try_parse_uuid(query)

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
        elif query:
            expertise_blob = func.coalesce(
                func.array_to_string(MentorProfile.expertise, " "),
                "",
            )
            expertise_match = expertise_blob.ilike(f"%{query}%")
            bio_match = func.coalesce(MentorProfile.bio, "").ilike(f"%{query}%")
            uid_match = cast(MentorProfile.user_id, String).ilike(f"%{query}%")
            stmt = stmt.where(or_(expertise_match, bio_match, uid_match))

        results = (await self._session.execute(stmt)).scalars().all()
        return [
            SearchResult(
                user_id=m.user_id,
                first_name=label_from_user_id(m.user_id),
                last_name=None,
                role=SearchRole.mentor,
                expertise=list(m.expertise or []),
                tier="PEER",
            )
            for m in results
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
        elif query:
            goals_blob = func.coalesce(
                func.array_to_string(MenteeProfile.learning_goals, " "),
                "",
            )
            goals_match = goals_blob.ilike(f"%{query}%")
            edu_match = func.coalesce(MenteeProfile.education_level, "").ilike(f"%{query}%")
            uid_match = cast(MenteeProfile.user_id, String).ilike(f"%{query}%")
            stmt = stmt.where(or_(goals_match, edu_match, uid_match))

        results = (await self._session.execute(stmt)).scalars().all()
        return [
            SearchResult(
                user_id=m.user_id,
                first_name=label_from_user_id(m.user_id),
                last_name=None,
                role=SearchRole.mentee,
                expertise=list(m.learning_goals or []),
                tier=None,
            )
            for m in results
        ]
