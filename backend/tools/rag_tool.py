"""
tools/rag_tool.py

RAG retrieval tool used by multiple agents (Summarization, Report Writer,
and for the "What did I research last month?" follow-up flow) to query
the ChromaDB knowledge base built by the Knowledge Base Agent.

Embeddings are generated locally and for free via sentence-transformers
(BAAI/bge-small-en-v1.5) — no embedding API costs.

Note: the actual write path (storing embeddings) lives in
`rag/chroma_service.py`. This tool is read-only — it powers agent-side
*retrieval* during a run.

IMPORTANT — lazy connection: the ChromaDB client/collection is created on
first actual use (`_ensure_collection()`), NOT in `__init__` or at module
import time. An earlier version connected eagerly in `__init__` and
instantiated a module-level singleton at import time, which meant the
entire FastAPI app would fail to even *start* if ChromaDB happened to still
be booting (a real risk with `docker compose up` bringing services up in
parallel) — a classic eager-initialization footgun. Connecting lazily, with
retry, means a slow/restarting Chroma only affects requests that actually
need it, not the whole process.
"""

from __future__ import annotations

import logging

import chromadb
from chromadb.api.models.Collection import Collection
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from core.config import settings
from rag.embedding_service import get_embedding_function

logger = logging.getLogger(__name__)


class KnowledgeSearchInput(BaseModel):
    query: str = Field(..., description="Natural language query to search the knowledge base for")
    research_session_id: str | None = Field(
        default=None, description="If set, restrict search to chunks from this research session only"
    )
    user_id: str | None = Field(
        default=None, description="If set, restrict search to chunks owned by this user (cross-session recall)"
    )
    top_k: int = Field(default=5, ge=1, le=20)


class KnowledgeBaseSearchTool(BaseTool):
    name: str = "knowledge_base_search"
    description: str = (
        "Semantically search the vector knowledge base (ChromaDB) for relevant "
        "previously-extracted content chunks. Use this to retrieve supporting "
        "evidence while summarizing/writing, or to answer questions like "
        "'what did I research last month?' by searching across past sessions."
    )
    args_schema: type[BaseModel] = KnowledgeSearchInput

    # Pydantic v2 private attributes — not connected until first real use.
    _client: chromadb.ClientAPI | None = PrivateAttr(default=None)
    _collection: Collection | None = PrivateAttr(default=None)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(Exception),
    )
    def _ensure_collection(self) -> Collection:
        """Connects to ChromaDB on first use only, retrying transient startup races."""
        if self._collection is None:
            self._client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
            self._collection = self._client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                embedding_function=get_embedding_function(),
            )
        return self._collection

    def _run(
        self,
        query: str,
        research_session_id: str | None = None,
        user_id: str | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        where_filter: dict = {}
        if research_session_id:
            where_filter["research_session_id"] = research_session_id
        if user_id:
            where_filter["user_id"] = user_id

        try:
            collection = self._ensure_collection()
            results = collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_filter or None,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("ChromaDB query failed: %s", exc)
            return []

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]])[0]

        return [
            {
                "chroma_vector_id": vec_id,
                "text": doc,
                "metadata": meta,
                "relevance_score": round(1 - dist, 4) if dist is not None else None,
            }
            for vec_id, doc, meta, dist in zip(ids, documents, metadatas, distances)
        ]


# Module-level instance — safe to create at import time now, since the
# constructor (inherited from BaseTool/pydantic) does nothing network-bound;
# the actual ChromaDB connection only happens inside `_run()` -> `_ensure_collection()`.
knowledge_base_search_tool = KnowledgeBaseSearchTool()
