from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    @property
    def embedding_dim(self) -> int: ...

    async def generate_embedding(self, text: str) -> list[float]: ...
