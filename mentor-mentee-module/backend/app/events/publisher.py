import json
import logging

logger = logging.getLogger(__name__)


def publish_event(topic: str, payload: dict) -> None:
    """Stub publisher — replace with Pub/Sub in production."""
    logger.info("publish_event topic=%s payload=%s", topic, json.dumps(payload, default=str))
