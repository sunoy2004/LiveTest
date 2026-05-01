import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MenteeProfile, MentorProfile, MentorTier, User
from app.schemas.profile import MenteeProfileCreate, MentorProfileCreate
from app.utils.display_name import from_email


_TIER_IDS = frozenset({"PEER", "PROFESSIONAL", "EXPERT"})

class ProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_mentee_profile(self, user_id: uuid.UUID, data: MenteeProfileCreate) -> MenteeProfile:
        existing = await self._session.scalar(
            select(MenteeProfile).where(MenteeProfile.user_id == user_id),
        )
        if existing:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Mentee profile already exists for this user",
            )

        profile = MenteeProfile(
            user_id=user_id,
            learning_goals=list(data.learning_goals) if data.learning_goals else [],
            education_level=data.education_level,
        )
        self._session.add(profile)
        try:
            await self._session.commit()
        except IntegrityError as e:
            await self._session.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Could not create mentee profile",
            ) from e
        await self._session.refresh(profile)
        return profile

    async def create_mentor_profile(self, user_id: uuid.UUID, data: MentorProfileCreate) -> MentorProfile:
        existing = await self._session.scalar(
            select(MentorProfile).where(MentorProfile.user_id == user_id),
        )
        if existing:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Mentor profile already exists for this user",
            )

        profile = MentorProfile(
            user_id=user_id,
            bio=getattr(data, "bio", None),
            expertise=list(data.expertise_areas) if hasattr(data, "expertise_areas") else [],
            experience_years=getattr(data, "experience_years", 0),
        )
        self._session.add(profile)
        try:
            await self._session.commit()
        except IntegrityError as e:
            await self._session.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Could not create mentor profile",
            ) from e
        await self._session.refresh(profile)
        return profile

    async def get_profile_bundle(self, user_id: uuid.UUID) -> tuple[MenteeProfile | None, MentorProfile | None]:
        mentee = await self._session.scalar(
            select(MenteeProfile).where(MenteeProfile.user_id == user_id),
        )
        mentor = await self._session.scalar(
            select(MentorProfile).where(MentorProfile.user_id == user_id),
        )
        return mentee, mentor

    async def get_mentor_public_detail(self, mentor_user_id: uuid.UUID) -> dict | None:
        """Public mentor card (AI match / profile modal) — keyed by mentor `user_id`."""
        mp = await self._session.scalar(
            select(MentorProfile).where(MentorProfile.user_id == mentor_user_id),
        )
        if mp is None:
            return None
        user = await self._session.get(User, mentor_user_id)
        tier_row = await self._session.scalar(select(MentorTier).where(MentorTier.user_id == mentor_user_id))
        raw = (tier_row.tier if tier_row else "PEER").strip().upper()
        tier_id = raw if raw in _TIER_IDS else "PEER"
        uid = str(mp.user_id)
        return {
            "email": user.email if user else "",
            "display_name": from_email(user.email if user else None),
            "mentor_profile": {
                "id": uid,
                "user_id": uid,
                "tier_id": tier_id,
                "pricing_tier": tier_id.lower(),
                "base_credit_override": None,
                "is_accepting_requests": True,
                "expertise_areas": list(mp.expertise or []),
                "total_hours_mentored": 0,
                "headline": None,
                "bio": mp.bio,
                "current_title": None,
                "current_company": None,
                "years_experience": mp.experience_years,
                "professional_experiences": None,
            },
        }
