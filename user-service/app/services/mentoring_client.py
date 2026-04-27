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
