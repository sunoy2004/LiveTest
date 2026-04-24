from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock

from app.api.deps import get_recommendation_service, get_feedback_service
from app.main import app


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_get_recommendations_mocked_service(client):
    m = MagicMock()
    m.recommend = AsyncMock(
        return_value=[{"mentor_id": "550e8400-e29b-41d4-a716-446655440000", "score": 0.75}],
    )
    app.dependency_overrides[get_recommendation_service] = lambda: m
    app.dependency_overrides[get_feedback_service] = lambda: MagicMock()
    try:
        os.environ["AI_TRUST_GATEWAY_HEADERS"] = "true"
        r = client.get(
            "/recommendations",
            params={
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "limit": 5,
            },
            headers={"X-User-Id": "550e8400-e29b-41d4-a716-446655440000"},
        )
    finally:
        app.dependency_overrides.clear()
        os.environ.pop("AI_TRUST_GATEWAY_HEADERS", None)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["score"] == 0.75


def test_feedback_mocked(client):
    fb = MagicMock()
    fb.record = AsyncMock(
        return_value={"ok": True, "weight": -100},
    )
    app.dependency_overrides[get_feedback_service] = lambda: fb
    app.dependency_overrides[get_recommendation_service] = lambda: MagicMock()
    try:
        os.environ["AI_TRUST_GATEWAY_HEADERS"] = "true"
        r = client.post(
            "/recommendations/feedback",
            json={
                "target_user_id": "550e8400-e29b-41d4-a716-446655440001",
                "interaction_type": "REJECTED_SUGGESTION",
            },
            headers={"X-User-Id": "550e8400-e29b-41d4-a716-446655440000"},
        )
    finally:
        app.dependency_overrides.clear()
        os.environ.pop("AI_TRUST_GATEWAY_HEADERS", None)
    assert r.status_code == 200
    fb.record.assert_awaited()
