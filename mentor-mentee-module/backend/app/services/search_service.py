import uuid
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import MenteeProfile, MentorProfile, User
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
        stmt = select(MentorProfile, User.email).join(User, MentorProfile.user_id == User.user_id).limit(limit)

        if user_id is not None:
            stmt = stmt.where(MentorProfile.user_id == user_id)
        elif query:
            expertise_match = MentorProfile.expertise.any(query)
            email_match = User.email.ilike(f"%{query}%")
            stmt = stmt.where(or_(expertise_match, email_match))

        results = (await self._session.execute(stmt)).all()
        return [
            SearchResult(
                user_id=m.user_id,
                first_name=email.split("@")[0].replace(".", " ").replace("_", " ").title(),
                last_name=None,
                role=SearchRole.mentor,
                expertise=list(m.expertise or []),
                tier="PEER", # Default tier for now
            )
            for m, email in results
        ]

    async def _search_mentees(
        self,
        *,
        query: str,
        user_id: uuid.UUID | None,
        limit: int,
    ) -> list[SearchResult]:
        stmt = select(MenteeProfile, User.email).join(User, MenteeProfile.user_id == User.user_id).limit(limit)

        if user_id is not None:
            stmt = stmt.where(MenteeProfile.user_id == user_id)
        elif query:
            goals_match = MenteeProfile.learning_goals.any(query)
            email_match = User.email.ilike(f"%{query}%")
            stmt = stmt.where(or_(goals_match, email_match))

        results = (await self._session.execute(stmt)).all()
        return [
            SearchResult(
                user_id=m.user_id,
                first_name=email.split("@")[0].replace(".", " ").replace("_", " ").title(),
                last_name=None,
                role=SearchRole.mentee,
                expertise=list(m.learning_goals or []),
                tier=None,
            )
            for m, email in results
        ]
