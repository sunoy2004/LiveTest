import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MenteeProfile, MentorProfile
from app.schemas.profile import MenteeProfileCreate, MentorProfileCreate
from app.services.gamification_transactions import fetch_wallet_balance_from_gamification
from app.utils.profile_display_name import mentor_display_name_map


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
        if mentee is not None:
            balance = await fetch_wallet_balance_from_gamification(user_id)
            if balance is not None:
                mentee.cached_credit_score = balance
                try:
                    await self._session.commit()
                    await self._session.refresh(mentee)
                except Exception:
                    await self._session.rollback()
        return mentee, mentor

    async def get_mentor_public_detail(self, mentor_user_id: uuid.UUID) -> dict | None:
        """Public mentor card (AI match / profile modal) — keyed by mentor `user_id`."""
        mp = await self._session.scalar(
            select(MentorProfile).where(MentorProfile.user_id == mentor_user_id),
        )
        if mp is None:
            return None
        names = await mentor_display_name_map(self._session, [mentor_user_id])
        display_title = names.get(mentor_user_id, "")
        # Production DB may omit mentor_profiles.tier_id; UI still expects a tier label.
        tier_id = "PEER"
        uid = str(mp.user_id)
        return {
            "email": "",
            "display_name": display_title,
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
