from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING

from app.ai.opensource import OpenSourceEmbeddingProvider
from app.infra.settings import get_settings

if TYPE_CHECKING:
    from app.ai.protocol import EmbeddingProvider

log = logging.getLogger(__name__)


@lru_cache
def get_embedding_provider() -> "EmbeddingProvider":
    s = get_settings()
    if s.use_vertex_provider:
        from app.ai.vertex import VertexAIEmbeddingProvider

        return VertexAIEmbeddingProvider(
            model_name=s.vertex_embedding_model,
            embedding_dim=s.embedding_dim,
            gcp_location=s.gcp_location,
        )
    return OpenSourceEmbeddingProvider(
        s.opensource_model,
        embedding_dim=s.embedding_dim,
    )
