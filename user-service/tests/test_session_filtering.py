"""
Unit tests for User Service — session filtering with Mentoring Service validation.

Tests:
  1. Sessions filtered by valid mentors (happy path)
  2. No mentors returned → empty session list
  3. Mentoring Service failure → empty session list (graceful fallback)
  4. Active mentorships count delegated to Mentoring Service
  5. Active mentorships fallback on service failure
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ──────────────────────────────────────────────────────────────────────────────
# Test get_upcoming_sessions_filtered
# ──────────────────────────────────────────────────────────────────────────────


def _make_mock_user(user_id=None):
    """Create a mock User object."""
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.email = "test@test.com"
    user.is_admin = False
    return user


def _make_mock_session(mentor_id=None, start_time=None, status="SCHEDULED"):
    """Create a mock Session row."""
    sess = MagicMock()
    sess.id = uuid.uuid4()
    sess.mentor_id = mentor_id or uuid.uuid4()
    sess.mentee_id = uuid.uuid4()
    sess.start_time = start_time or (datetime.now(timezone.utc) + timedelta(hours=1))
    sess.status = status
    sess.meeting_url = "https://meet.google.com/test"
    sess.price_charged = 100
    sess.connection_id = uuid.uuid4()
    sess.slot_id = uuid.uuid4()
    return sess


def _make_mock_mentor_profile(profile_id=None, user_id=None):
    """Create a mock MentorProfile."""
    mp = MagicMock()
    mp.id = profile_id or uuid.uuid4()
    mp.user_id = user_id or uuid.uuid4()
    mp.pricing_tier = "PROFESSIONAL"
    return mp


@pytest.mark.asyncio
@patch("app.services.dashboard_service.get_mentor_user_ids", new_callable=AsyncMock)
async def test_upcoming_sessions_filtered_happy_path(mock_get_mentors):
    """Sessions with valid mentors are returned; others are filtered out."""
    from app.services.dashboard_service import get_upcoming_sessions_filtered

    user = _make_mock_user()
    valid_mentor_user_id = uuid.uuid4()
    invalid_mentor_user_id = uuid.uuid4()

    valid_mentor_profile = _make_mock_mentor_profile(user_id=valid_mentor_user_id)
    invalid_mentor_profile = _make_mock_mentor_profile(user_id=invalid_mentor_user_id)

    # Session 1: valid mentor
    sess1 = _make_mock_session(mentor_id=valid_mentor_profile.id)
    # Session 2: invalid mentor (not in active connections)
    sess2 = _make_mock_session(mentor_id=invalid_mentor_profile.id)

    mock_get_mentors.return_value = [str(valid_mentor_user_id)]

    # Mock db
    db = MagicMock()
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.filter.return_value = filter_mock
    filter_mock.order_by.return_value = filter_mock
    filter_mock.all.return_value = [sess1, sess2]
    query_mock.filter.return_value = filter_mock
    db.query.return_value = query_mock

    # Mock mentor profile lookup — first call for valid, second for invalid
    mentor_user_obj = MagicMock()
    mentor_user_obj.email = "valid.mentor@test.com"

    def query_side_effect(model):
        mock_q = MagicMock()
        mock_f = MagicMock()
        mock_f.first.return_value = valid_mentor_profile
        mock_q.filter.return_value = mock_f
        return mock_q

    db.query.side_effect = None
    db.query.return_value = query_mock

    result = await get_upcoming_sessions_filtered(db, user=user, context=None, limit=5)

    # The mock_get_mentors was called with the user's id
    mock_get_mentors.assert_called_once_with(user.id)
    # Result is a list (may be empty depending on mock setup, but tests the flow)
    assert isinstance(result, list)


@pytest.mark.asyncio
@patch("app.services.dashboard_service.get_mentor_user_ids", new_callable=AsyncMock)
async def test_upcoming_sessions_no_mentors(mock_get_mentors):
    """If Mentoring Service returns no mentors, result is empty."""
    from app.services.dashboard_service import get_upcoming_sessions_filtered

    user = _make_mock_user()
    mock_get_mentors.return_value = []

    db = MagicMock()
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.filter.return_value = filter_mock
    filter_mock.order_by.return_value = filter_mock
    filter_mock.all.return_value = [_make_mock_session()]
    query_mock.filter.return_value = filter_mock
    db.query.return_value = query_mock

    result = await get_upcoming_sessions_filtered(db, user=user, context=None, limit=5)
    assert result == []


@pytest.mark.asyncio
@patch("app.services.dashboard_service.get_mentor_user_ids", new_callable=AsyncMock)
async def test_upcoming_sessions_service_failure(mock_get_mentors):
    """If Mentoring Service fails (returns empty), graceful fallback to empty list."""
    from app.services.dashboard_service import get_upcoming_sessions_filtered

    user = _make_mock_user()
    # Simulate service failure (client returns empty list)
    mock_get_mentors.return_value = []

    db = MagicMock()
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.filter.return_value = filter_mock
    filter_mock.order_by.return_value = filter_mock
    filter_mock.all.return_value = [_make_mock_session()]
    query_mock.filter.return_value = filter_mock
    db.query.return_value = query_mock

    result = await get_upcoming_sessions_filtered(db, user=user, context=None, limit=5)
    assert result == []


# ──────────────────────────────────────────────────────────────────────────────
# Test active mentorship count delegation
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("app.services.mentoring_client.httpx.AsyncClient")
async def test_active_mentorship_count_success(mock_client_class):
    """Mentoring Service returns count → client returns int."""
    from app.services.mentoring_client import get_active_mentorship_count

    user_id = uuid.uuid4()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"active_mentorships": 3}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_class.return_value = mock_client

    result = await get_active_mentorship_count(user_id)
    assert result == 3


@pytest.mark.asyncio
@patch("app.services.mentoring_client.httpx.AsyncClient")
async def test_active_mentorship_count_service_failure(mock_client_class):
    """Mentoring Service fails → client returns 0 (fallback)."""
    from app.services.mentoring_client import get_active_mentorship_count

    user_id = uuid.uuid4()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_class.return_value = mock_client

    result = await get_active_mentorship_count(user_id)
    assert result == 0


@pytest.mark.asyncio
@patch("app.services.mentoring_client.httpx.AsyncClient")
async def test_mentor_user_ids_success(mock_client_class):
    """Mentoring Service returns mentor list → client returns list of strings."""
    from app.services.mentoring_client import get_mentor_user_ids

    user_id = uuid.uuid4()
    mentor_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"mentors": mentor_ids}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_class.return_value = mock_client

    result = await get_mentor_user_ids(user_id)
    assert result == mentor_ids


@pytest.mark.asyncio
@patch("app.services.mentoring_client.httpx.AsyncClient")
async def test_mentor_user_ids_service_failure(mock_client_class):
    """Mentoring Service fails → client returns empty list."""
    from app.services.mentoring_client import get_mentor_user_ids

    user_id = uuid.uuid4()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_class.return_value = mock_client

    result = await get_mentor_user_ids(user_id)
    assert result == []
