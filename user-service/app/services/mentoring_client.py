import os
import httpx
import logging
import uuid
from typing import List, Dict

logger = logging.getLogger(__name__)

# Usually set in GCP Cloud Run environment variables
MENTORING_SERVICE_URL = os.getenv("MENTORING_SERVICE_URL", "http://localhost:8000")

async def get_active_connections_from_mentoring_service(user_id: uuid.UUID) -> List[Dict]:
    """
    Calls the Mentoring Service to fetch the real active connections for a user.
    Used as a fallback/bridge when Redis sync is not available.
    """
    url = f"{MENTORING_SERVICE_URL}/api/v1/requests/connections"
    headers = {"X-User-Id": str(user_id)}
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning("Mentoring service returned %d: %s", response.status_code, response.text)
                return []
    except Exception as e:
        logger.error("Failed to connect to Mentoring Service at %s: %s", url, e)
        return []

async def get_goals_from_mentoring_service(connection_id: uuid.UUID) -> List[Dict]:
    """Fetch goals for a connection from the Mentoring Service."""
    url = f"{MENTORING_SERVICE_URL}/api/v1/requests/connections/{connection_id}/goals"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            return response.json() if response.status_code == 200 else []
    except Exception as e:
        logger.error("Failed to fetch goals from Mentoring Service: %s", e)
        return []

async def get_vault_from_mentoring_service(connection_id: uuid.UUID) -> List[Dict]:
    """Fetch vault items for a connection from the Mentoring Service."""
    url = f"{MENTORING_SERVICE_URL}/api/v1/requests/connections/{connection_id}/vault"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            return response.json() if response.status_code == 200 else []
    except Exception as e:
        logger.error("Failed to fetch vault from Mentoring Service: %s", e)
        return []

async def get_admin_connections_from_mentoring_service() -> List[Dict]:
    """Admin only: fetch all connections across the platform."""
    url = f"{MENTORING_SERVICE_URL}/api/v1/requests/admin/connections"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            return response.json() if response.status_code == 200 else []
    except Exception as e:
        logger.error("Failed to fetch admin connections from Mentoring Service: %s", e)
        return []

async def get_session_history_from_mentoring_service(connection_id: uuid.UUID) -> List[Dict]:
    """Fetch session history (duration_hours, start_time) for a connection."""
    url = f"{MENTORING_SERVICE_URL}/api/v1/requests/connections/{connection_id}/history"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            return response.json() if response.status_code == 200 else []
    except Exception as e:
        logger.error("Failed to fetch session history from Mentoring Service: %s", e)
        return []


# ─── NEW DATA CONTRACT CLIENTS ────────────────────────────────────────────────
# These use the dedicated /mentorships/* endpoints which enforce correct
# service boundaries (Mentoring Service is sole owner of mentorship data).


async def get_active_mentorship_count(user_id: uuid.UUID) -> int:
    """
    Call Mentoring Service's dedicated endpoint to get the count of ACTIVE
    mentorship connections for a user (counting both mentor and mentee roles).

    Falls back to 0 on any failure.
    """
    url = f"{MENTORING_SERVICE_URL}/api/v1/mentorships/count"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params={"user_id": str(user_id)})
            if response.status_code == 200:
                data = response.json()
                return data.get("active_mentorships", 0)
            else:
                logger.warning(
                    "Mentoring service /mentorships/count returned %d: %s",
                    response.status_code, response.text,
                )
                return 0
    except Exception as e:
        logger.error("Failed to fetch active mentorship count: %s", e)
        return 0


async def get_mentor_user_ids(user_id: uuid.UUID) -> List[str]:
    """
    Call Mentoring Service's dedicated endpoint to get the list of
    mentor user_ids for a user's ACTIVE mentorship connections.

    Used by the dashboard to filter upcoming sessions to only those
    with valid, active mentor relationships.

    Falls back to an empty list on any failure.
    """
    url = f"{MENTORING_SERVICE_URL}/api/v1/mentorships/mentors"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params={"user_id": str(user_id)})
            if response.status_code == 200:
                data = response.json()
                return data.get("mentors", [])
            else:
                logger.warning(
                    "Mentoring service /mentorships/mentors returned %d: %s",
                    response.status_code, response.text,
                )
                return []
    except Exception as e:
        logger.error("Failed to fetch mentor user_ids: %s", e)
        return []


async def get_mentee_user_ids(user_id: uuid.UUID) -> List[str]:
    """
    Call Mentoring Service's dedicated endpoint to get the list of
    mentee user_ids for a user's ACTIVE mentorship connections.
    """
    url = f"{MENTORING_SERVICE_URL}/api/v1/mentorships/mentees"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params={"user_id": str(user_id)})
            if response.status_code == 200:
                data = response.json()
                return data.get("mentees", [])
            else:
                logger.warning(
                    "Mentoring service /mentorships/mentees returned %d: %s",
                    response.status_code, response.text,
                )
                return []
    except Exception as e:
        logger.error("Failed to fetch mentee user_ids: %s", e)
        return []


