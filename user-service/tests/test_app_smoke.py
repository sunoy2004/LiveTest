"""Smoke tests for the trimmed User Service (auth + internal + health)."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


@patch("app.realtime.redis_listener.stop_listener", new_callable=AsyncMock)
@patch("app.realtime.redis_listener.start_listener", new_callable=AsyncMock)
def test_health(_mock_start: AsyncMock, _mock_stop: AsyncMock) -> None:
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
