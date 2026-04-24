from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import NotificationLog


def record_notification(
    db: Session,
    *,
    topic: str,
    event_type: str,
    payload: dict[str, Any],
) -> NotificationLog:
    row = NotificationLog(
        topic=topic,
        event_type=event_type,
        payload_json=json.dumps(payload, default=str),
    )
    db.add(row)
    return row