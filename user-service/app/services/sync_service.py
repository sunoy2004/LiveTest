import logging
import uuid
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import MentorshipConnection

logger = logging.getLogger(__name__)

async def sync_connection_accepted(data: dict) -> None:
    """
    Syncs a mentorship connection from an external service (Mentoring Service)
    into the local User Service database to keep dashboard stats accurate.
    """
    payload = data.get("payload") or data
    conn_id_str = payload.get("connection_id")
    mentor_id_str = payload.get("mentor_id")
    mentee_id_str = payload.get("mentee_id")

    if not all([conn_id_str, mentor_id_str, mentee_id_str]):
        logger.warning("Invalid connection sync payload: %s", data)
        return

    try:
        conn_id = uuid.UUID(conn_id_str)
        mentor_id = uuid.UUID(mentor_id_str)
        mentee_id = uuid.UUID(mentee_id_str)
    except ValueError:
        logger.warning("Invalid UUIDs in sync payload: %s", data)
        return

    db: Session = SessionLocal()
    try:
        # Check if already exists
        existing = db.query(MentorshipConnection).filter(MentorshipConnection.id == conn_id).first()
        if existing:
            logger.info("Connection %s already synced", conn_id)
            return

        new_conn = MentorshipConnection(
            id=conn_id,
            mentor_id=mentor_id,
            mentee_id=mentee_id,
            status="ACTIVE"
        )
        db.add(new_conn)
        db.commit()
        logger.info("Successfully synced connection %s to User Service DB", conn_id)
    except Exception as e:
        db.rollback()
        logger.error("Failed to sync connection %s: %s", conn_id, e)
    finally:
        db.close()
