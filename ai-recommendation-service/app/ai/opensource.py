from __future__ import annotations

import asyncio
import logging
from typing import ClassVar

import numpy as np

log = logging.getLogger(__name__)


class OpenSourceEmbeddingProvider:
    """sentence-transformers (CPU) — 768-d all-mpnet-base-v2 by default."""

    def __init__(self, model_name: str, embedding_dim: int = 768) -> None:
        self._model_name = model_name
        self._embedding_dim = embedding_dim
        self._model = None  # lazy

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # lazy import (heavy)

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def _encode_sync(self, text: str) -> list[float]:
        model = self._load()
        v = model.encode(
            text or " ",
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        arr = np.asarray(v, dtype=np.float32).reshape(-1)
        out = arr.tolist()
        if len(out) != self._embedding_dim:
            raise ValueError(
                f"Model returned dim {len(out)} but expected {self._embedding_dim}",
            )
        return out

    async def generate_embedding(self, text: str) -> list[float]:
        return await asyncio.to_thread(self._encode_sync, text)
