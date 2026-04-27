import asyncio
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import GuardianConsentStatus, MenteeProfile, MentorProfile, MentorTier


def _u(n: int) -> uuid.UUID:
    # Deterministic UUIDs for repeatable seeds
    return uuid.UUID(f"00000000-0000-0000-0000-{n:012d}")


async def _ensure_tiers(session: AsyncSession) -> None:
    tiers = (await session.scalars(select(MentorTier))).all()
    if tiers:
        return

    session.add_all(
        [
            MentorTier(tier_id="PEER", tier_name="Peer", session_credit_cost=50),
            MentorTier(tier_id="PROFESSIONAL", tier_name="Professional", session_credit_cost=100),
            MentorTier(tier_id="EXPERT", tier_name="Expert", session_credit_cost=250),
        ]
    )
    await session.flush()


async def _seed_mentors(session: AsyncSession) -> None:
    mentors: list[tuple[uuid.UUID, str, str, bool, list[str], int]] = [
        (_u(1), "Aisha Khan", "EXPERT", True, ["python", "ml", "fastapi"], 1200),
        (_u(2), "Rohan Mehta", "PROFESSIONAL", True, ["nodejs", "typescript", "react"], 540),
        (_u(3), "Mei Lin", "EXPERT", True, ["data engineering", "postgres", "airflow"], 980),
        (_u(4), "Carlos Silva", "PEER", True, ["java", "spring", "microservices"], 180),
        (_u(5), "Fatima Noor", "PROFESSIONAL", False, ["product management", "roadmaps", "leadership"], 430),
        (_u(6), "Noah Johnson", "EXPERT", True, ["devops", "kubernetes", "terraform"], 1500),
        (_u(7), "Priya Sharma", "PROFESSIONAL", True, ["android", "kotlin", "system design"], 610),
        (_u(8), "Ethan Brooks", "PEER", True, ["ui/ux", "figma", "design systems"], 95),
        (_u(9), "Zara Ali", "EXPERT", True, ["security", "oauth", "appsec"], 860),
        (_u(10), "Hiro Tanaka", "PROFESSIONAL", True, ["golang", "distributed systems", "grpc"], 720),
    ]

    existing_user_ids = set(
        (await session.scalars(select(MentorProfile.user_id))).all()
    )

    for user_id, full_name, tier_id, accepting, expertise, hours in mentors:
        if user_id in existing_user_ids:
            continue
        session.add(
            MentorProfile(
                user_id=user_id,
                full_name=full_name,
                tier_id=tier_id,
                is_accepting_requests=accepting,
                expertise_areas=expertise,
                total_hours_mentored=hours,
            )
        )

    await session.flush()


async def _seed_mentees(session: AsyncSession) -> None:
    mentees: list[tuple[uuid.UUID, str, list[str], str, bool, GuardianConsentStatus, int]] = [
        (_u(101), "Ananya Das", ["python", "fastapi", "sql"], "UNDERGRAD", False, GuardianConsentStatus.NOT_REQUIRED, 710),
        (_u(102), "Omar Rahman", ["react", "typescript", "interviews"], "UNDERGRAD", False, GuardianConsentStatus.NOT_REQUIRED, 650),
        (_u(103), "Sophia Lee", ["machine learning", "pandas", "projects"], "GRAD", False, GuardianConsentStatus.NOT_REQUIRED, 780),
        (_u(104), "Jacob Miller", ["docker", "kubernetes", "ci/cd"], "PROFESSIONAL", False, GuardianConsentStatus.NOT_REQUIRED, 600),
        (_u(105), "Mina Park", ["system design", "distributed systems"], "PROFESSIONAL", False, GuardianConsentStatus.NOT_REQUIRED, 720),
        (_u(106), "Rahul Verma", ["android", "kotlin", "compose"], "UNDERGRAD", False, GuardianConsentStatus.NOT_REQUIRED, 590),
        (_u(107), "Lina Gomez", ["ui/ux", "figma", "portfolio"], "UNDERGRAD", False, GuardianConsentStatus.NOT_REQUIRED, 640),
        (_u(108), "Ben Carter", ["security", "owasp", "oauth"], "PROFESSIONAL", False, GuardianConsentStatus.NOT_REQUIRED, 680),
        (_u(109), "Sara Ahmed", ["postgres", "data modeling", "performance"], "GRAD", False, GuardianConsentStatus.NOT_REQUIRED, 760),
        (_u(110), "Ibrahim Hassan", ["golang", "grpc", "backend"], "UNDERGRAD", True, GuardianConsentStatus.PENDING, 500),
    ]

    existing_user_ids = set(
        (await session.scalars(select(MenteeProfile.user_id))).all()
    )

    for user_id, full_name, goals, edu, is_minor, consent, score in mentees:
        if user_id in existing_user_ids:
            continue
        session.add(
            MenteeProfile(
                user_id=user_id,
                full_name=full_name,
                learning_goals=goals,
                education_level=edu,
                is_minor=is_minor,
                guardian_consent_status=consent,
                cached_credit_score=0,
            )
        )

    await session.flush()


async def main() -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        await _ensure_tiers(session)
        await _seed_mentors(session)
        await _seed_mentees(session)
        await session.commit()

        mentors_count = await session.scalar(select(func.count()).select_from(MentorProfile))
        mentees_count = await session.scalar(select(func.count()).select_from(MenteeProfile))
        print(f"Mentors in DB: {mentors_count}, Mentees in DB: {mentees_count}")

    await engine.dispose()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())

