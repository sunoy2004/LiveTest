"""
Unit tests for Mentoring Service — mentorship count and mentors list endpoints.

Tests:
  1. Active mentorship count for a user who is only a mentee
  2. Active mentorship count for a user who is only a mentor
  3. Active mentorship count for a user who is both mentor and mentee
  4. Active mentorship count for unknown user (returns 0)
  5. Mentors list for a mentee
  6. Mentors list for unknown user (returns empty)
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ──────────────────────────────────────────────────────────────────────────────
# Test get_active_mentorship_count endpoint logic
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mentorship_count_mentee_only():
    """User is only a mentee with 2 active connections → count = 2."""
    from app.api.v1.mentorships import get_active_mentorship_count

    user_id = uuid.uuid4()
    mentee_profile_id = uuid.uuid4()

    db = AsyncMock()
    # First scalar call → mentee_id
    # Second scalar call → mentor_id (None)
    # Third scalar call → count
    db.scalar = AsyncMock(side_effect=[mentee_profile_id, None, 2])

    result = await get_active_mentorship_count(user_id=user_id, db=db)
    assert result == {"active_mentorships": 2}


@pytest.mark.asyncio
async def test_mentorship_count_mentor_only():
    """User is only a mentor with 3 active connections → count = 3."""
    from app.api.v1.mentorships import get_active_mentorship_count

    user_id = uuid.uuid4()
    mentor_profile_id = uuid.uuid4()

    db = AsyncMock()
    db.scalar = AsyncMock(side_effect=[None, mentor_profile_id, 3])

    result = await get_active_mentorship_count(user_id=user_id, db=db)
    assert result == {"active_mentorships": 3}


@pytest.mark.asyncio
async def test_mentorship_count_both_roles():
    """User is both mentor and mentee with 5 total connections → count = 5."""
    from app.api.v1.mentorships import get_active_mentorship_count

    user_id = uuid.uuid4()
    mentee_profile_id = uuid.uuid4()
    mentor_profile_id = uuid.uuid4()

    db = AsyncMock()
    db.scalar = AsyncMock(side_effect=[mentee_profile_id, mentor_profile_id, 5])

    result = await get_active_mentorship_count(user_id=user_id, db=db)
    assert result == {"active_mentorships": 5}


@pytest.mark.asyncio
async def test_mentorship_count_unknown_user():
    """User has no profiles → count = 0."""
    from app.api.v1.mentorships import get_active_mentorship_count

    user_id = uuid.uuid4()

    db = AsyncMock()
    db.scalar = AsyncMock(side_effect=[None, None])

    result = await get_active_mentorship_count(user_id=user_id, db=db)
    assert result == {"active_mentorships": 0}


@pytest.mark.asyncio
async def test_mentors_list_for_mentee():
    """Mentee has 2 active mentors → returns 2 mentor user_ids."""
    from app.api.v1.mentorships import get_active_mentors_for_user

    user_id = uuid.uuid4()
    mentee_id = uuid.uuid4()
    mentor_uid_1 = uuid.uuid4()
    mentor_uid_2 = uuid.uuid4()

    db = AsyncMock()
    # First scalar → mentee profile id
    db.scalar = AsyncMock(return_value=mentee_id)

    # Execute returns scalars
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mentor_uid_1, mentor_uid_2]
    db.execute = AsyncMock(return_value=mock_result)

    result = await get_active_mentors_for_user(user_id=user_id, db=db)
    assert result == {"mentors": [str(mentor_uid_1), str(mentor_uid_2)]}


@pytest.mark.asyncio
async def test_mentors_list_unknown_user():
    """User has no mentee profile → returns empty mentors list."""
    from app.api.v1.mentorships import get_active_mentors_for_user

    user_id = uuid.uuid4()

    db = AsyncMock()
    db.scalar = AsyncMock(return_value=None)

    result = await get_active_mentors_for_user(user_id=user_id, db=db)
    assert result == {"mentors": []}
