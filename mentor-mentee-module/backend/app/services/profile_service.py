import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MenteeProfile, MentorProfile, MentorTier
from app.models.enums import GuardianConsentStatus
from app.schemas.profile import MenteeProfileCreate, MentorProfileCreate


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

        consent = (
            GuardianConsentStatus.PENDING if data.is_minor else GuardianConsentStatus.NOT_REQUIRED
        )
        profile = MenteeProfile(
            user_id=user_id,
            learning_goals=list(data.learning_goals),
            education_level=data.education_level,
            is_minor=data.is_minor,
            guardian_consent_status=consent,
            cached_credit_score=0,
        )
        self._session.add(profile)
        try:
            await self._session.flush()
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

        tier = await self._session.get(MentorTier, data.tier_id)
        if tier is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown tier_id: {data.tier_id}",
            )

        profile = MentorProfile(
            user_id=user_id,
            tier_id=data.tier_id,
            is_accepting_requests=data.is_accepting_requests,
            expertise_areas=list(data.expertise_areas),
            total_hours_mentored=0,
        )
        self._session.add(profile)
        try:
            await self._session.flush()
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
