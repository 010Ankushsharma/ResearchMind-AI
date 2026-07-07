"""
rag/embedding_service.py

Local, free text embedding generation using sentence-transformers.

Model: BAAI/bge-small-en-v1.5
  - 384-dim embeddings, strong retrieval quality for its size, runs on CPU,
    no API key, no per-call cost — ideal for a free-tier-only stack.

Exposes a ChromaDB-compatible `EmbeddingFunction` so the same model is used
consistently for both writes (rag/chroma_service.py) and reads (tools/rag_tool.py).
"""

from __future__ import annotations

import logging
from functools import lru_cache

from chromadb import Documents, EmbeddingFunction, Embeddings
from sentence_transformers import SentenceTransformer

from core.config import settings

logger = logging.getLogger(__name__)

# BGE models recommend prefixing *queries* (not documents) with an instruction
# for better retrieval performance. We apply this inside `__call__` based on
# the `is_query` flag rather than globally, since Chroma calls embed both ways.
_BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def _load_model() -> SentenceTransformer:
    logger.info("Loading local embedding model: %s", settings.EMBEDDING_MODEL)
    return SentenceTransformer(settings.EMBEDDING_MODEL)


class LocalBGEEmbeddingFunction(EmbeddingFunction):
    """ChromaDB-compatible embedding function wrapping a local SentenceTransformer."""

    def __init__(self, is_query: bool = False):
        self.is_query = is_query
        self.model = _load_model()

    def __call__(self, input: Documents) -> Embeddings:  # noqa: A002 (Chroma's required signature)
        texts = list(input)
        if self.is_query:
            texts = [f"{_BGE_QUERY_INSTRUCTION}{t}" for t in texts]

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,  # cosine similarity works cleanly on normalized vectors
            show_progress_bar=False,
        )
        return embeddings.tolist()


@lru_cache(maxsize=1)
def get_embedding_function() -> LocalBGEEmbeddingFunction:
    """
    Shared embedding function for document storage (rag/chroma_service.py).
    Cached so the underlying model is only loaded into memory once per process.
    """
    return LocalBGEEmbeddingFunction(is_query=False)


@lru_cache(maxsize=1)
def get_query_embedding_function() -> LocalBGEEmbeddingFunction:
    """
    Shared embedding function for *query-time* retrieval (tools/rag_tool.py),
    which applies the BGE query instruction prefix for better recall.
    """
    return LocalBGEEmbeddingFunction(is_query=True)


def embed_texts(texts: list[str], is_query: bool = False) -> list[list[float]]:
    """Convenience helper for one-off embedding calls outside of Chroma's collection API."""
    fn = get_query_embedding_function() if is_query else get_embedding_function()
    return fn(texts)
