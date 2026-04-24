from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def client():
    with (
        patch(
            "app.main.run_bootstrap_with_retry",
            new_callable=AsyncMock,
        ) as _b,
        patch(
            "app.realtime.redis_listener.start_listener",
            new_callable=AsyncMock,
        ),
        patch(
            "app.realtime.redis_listener.stop_listener",
            new_callable=AsyncMock,
        ),
    ):
        _b.return_value = None
        from app.main import app

        with TestClient(app) as tc:
            yield tc
