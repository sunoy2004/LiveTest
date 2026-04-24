from __future__ import annotations

import pytest


class _Fixed768:
    embedding_dim = 768

    async def generate_embedding(self, text: str) -> list[float]:
        return [1.0 / 768.0] * 768


@pytest.mark.asyncio
async def test_deterministic_mock_embedding_length():
    p = _Fixed768()
    v = await p.generate_embedding("x")
    assert len(v) == 768
