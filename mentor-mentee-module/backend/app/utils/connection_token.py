"""Stable connection id for (mentor_user_id, mentee_user_id) composite mentorship_connections."""

import uuid


def mentoring_connection_token(mentor_user_id: uuid.UUID, mentee_user_id: uuid.UUID) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{mentor_user_id}:{mentee_user_id}"))
