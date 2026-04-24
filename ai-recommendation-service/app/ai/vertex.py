from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)


class VertexAIEmbeddingProvider:
    """Vertex AI text embeddings (optional; requires google-cloud + GCP project)."""

    def __init__(
        self,
        *,
        model_name: str,
        embedding_dim: int,
        gcp_location: str,
    ) -> None:
        self._model_name = model_name
        self._embedding_dim = embedding_dim
        self._gcp_location = gcp_location
        self._model = None

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    def _load(self):
        if self._model is not None:
            return self._model
        try:
            from vertexai.language_models import TextEmbeddingModel
        except ImportError as e:
            raise RuntimeError(
                "Vertex embeddings require: pip install -r requirements-vertex.txt"
            ) from e

        project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
        if not project:
            raise RuntimeError(
                "Vertex AI requires GOOGLE_CLOUD_PROJECT (or GCP_PROJECT) in the environment"
            )
        from vertexai import init as vertex_init

        vertex_init(project=project, location=self._gcp_location)
        self._model = TextEmbeddingModel.from_pretrained(self._model_name)
        return self._model

    async def generate_embedding(self, text: str) -> list[float]:
        # Vertex SDK is sync; run off the event loop
        import asyncio

        return await asyncio.to_thread(self._encode_sync, text or " ")

    def _encode_sync(self, text: str) -> list[float]:
        model = self._load()
        embeddings = model.get_embeddings([text])
        if not embeddings or not embeddings[0].values:
            raise RuntimeError("Vertex returned empty embedding")
        vec = [float(x) for x in embeddings[0].values]
        if len(vec) != self._embedding_dim:
            raise ValueError(
                f"Vertex embedding has dim {len(vec)}; set embedding_dim in settings to match model output"
            )
        return vec
