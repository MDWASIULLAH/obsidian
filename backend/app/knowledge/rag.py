"""
OBSIDIAN — Qdrant RAG Pipeline.

Retrieval-Augmented Generation pipeline using Qdrant for
semantic search over security knowledge bases (OWASP, MITRE,
CWE, CAPEC, CVE, secure coding guidelines).

Every RAG-enhanced response includes source citations.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)

from app.config import get_settings
from app.core.model_router import get_model_router

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════════════
# Collection Names
# ═══════════════════════════════════════════════════════════════════

COLLECTIONS = [
    "owasp_top10",
    "mitre_attack",
    "cwe",
    "capec",
    "cve",
    "secure_coding",
    "organization_policies",
]


class RAGService:
    """
    Qdrant-backed RAG pipeline for security knowledge retrieval.

    Provides:
    - Collection management
    - Document ingestion with chunking
    - Semantic search with metadata filtering
    - Reranking for improved precision
    - Citation-tracked retrieval
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client: AsyncQdrantClient | None = None
        self._url = settings.qdrant_url
        self._api_key = settings.qdrant_api_key
        self._prefix = settings.qdrant_collection_prefix
        self._router = get_model_router()
        self._embedding_dim = 1024  # nv-embedqa-e5-v5 dimension

    async def initialize(self) -> None:
        """Connect to Qdrant and ensure collections exist."""
        self._client = AsyncQdrantClient(
            url=self._url,
            api_key=self._api_key if self._api_key else None
        )

        # Create collections if they don't exist
        existing = await self._client.get_collections()
        existing_names = {c.name for c in existing.collections}

        for collection in COLLECTIONS:
            coll_name = f"{self._prefix}_{collection}"
            if coll_name not in existing_names:
                await self._client.create_collection(
                    collection_name=coll_name,
                    vectors_config=VectorParams(
                        size=self._embedding_dim,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info("Created Qdrant collection", name=coll_name)

        logger.info("Qdrant RAG service initialized", collections=len(COLLECTIONS))

    # ═══════════════════════════════════════════════════════════
    # Ingestion
    # ═══════════════════════════════════════════════════════════

    async def ingest_documents(
        self,
        collection: str,
        documents: list[dict[str, Any]],
        batch_size: int = 50,
    ) -> int:
        """
        Ingest documents into a collection.

        Each document should have:
          - text: The content to embed
          - metadata: Dict with source, title, category, severity, etc.
        """
        coll_name = f"{self._prefix}_{collection}"
        total_ingested = 0

        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            texts = [doc["text"] for doc in batch]

            # Generate embeddings
            embeddings = await self._router.embed(texts)

            points = []
            for doc, embedding in zip(batch, embeddings):
                point_id = str(uuid4())
                metadata = doc.get("metadata", {})
                metadata["text"] = doc["text"][:2000]  # Store truncated text

                points.append(PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=metadata,
                ))

            await self._client.upsert(
                collection_name=coll_name,
                points=points,
            )
            total_ingested += len(points)

        logger.info(
            "Documents ingested",
            collection=collection,
            count=total_ingested,
        )
        return total_ingested

    # ═══════════════════════════════════════════════════════════
    # Retrieval
    # ═══════════════════════════════════════════════════════════

    async def search(
        self,
        query: str,
        collections: list[str] | None = None,
        top_k: int = 5,
        severity_filter: str | None = None,
        category_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Semantic search across security knowledge bases.

        Args:
            query: Natural language search query
            collections: Specific collections to search (default: all)
            top_k: Number of results per collection
            severity_filter: Filter by severity level
            category_filter: Filter by category

        Returns:
            List of results with text, metadata, score, and source_id
        """
        target_collections = collections or COLLECTIONS

        # Embed the query
        query_embedding = await self._router.embed_single(query)

        # Build filter if needed
        search_filter = None
        conditions = []
        if severity_filter:
            conditions.append(
                FieldCondition(key="severity", match=MatchValue(value=severity_filter))
            )
        if category_filter:
            conditions.append(
                FieldCondition(key="category", match=MatchValue(value=category_filter))
            )
        if conditions:
            search_filter = Filter(must=conditions)

        all_results = []

        for collection in target_collections:
            coll_name = f"{self._prefix}_{collection}"
            try:
                results = await self._client.search(
                    collection_name=coll_name,
                    query_vector=query_embedding,
                    limit=top_k,
                    query_filter=search_filter,
                )

                for hit in results:
                    payload = hit.payload or {}
                    source_id = f"{collection}:{hit.id}"
                    all_results.append({
                        "text": payload.get("text", ""),
                        "source": collection,
                        "source_id": source_id,
                        "score": hit.score,
                        "title": payload.get("title", ""),
                        "category": payload.get("category", ""),
                        "severity": payload.get("severity", ""),
                        "cwe_id": payload.get("cwe_id", ""),
                        "url": payload.get("url", ""),
                    })
            except Exception as e:
                logger.warning(
                    "Collection search failed",
                    collection=collection,
                    error=str(e),
                )

        # Sort by score and return top results
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:top_k * 2]

    async def get_context_for_agent(
        self,
        query: str,
        agent_name: str,
        top_k: int = 5,
    ) -> str:
        """
        Get formatted RAG context for an agent's prompt.

        Returns a formatted string with source citations that
        the agent can reference in its findings.
        """
        results = await self.search(query, top_k=top_k)

        if not results:
            return ""

        context_parts = []
        for i, result in enumerate(results):
            source_id = result["source_id"]
            title = result.get("title", "Untitled")
            text = result["text"]

            context_parts.append(
                f"[{source_id}] **{title}** (Score: {result['score']:.2f})\n"
                f"{text}\n"
            )

        return "\n---\n".join(context_parts)

    # ═══════════════════════════════════════════════════════════
    # Collection Management
    # ═══════════════════════════════════════════════════════════

    async def get_collection_stats(self) -> dict[str, dict]:
        """Get stats for all collections."""
        stats = {}
        for collection in COLLECTIONS:
            coll_name = f"{self._prefix}_{collection}"
            try:
                info = await self._client.get_collection(coll_name)
                stats[collection] = {
                    "vectors_count": info.vectors_count,
                    "points_count": info.points_count,
                    "status": info.status.value if info.status else "unknown",
                }
            except Exception:
                stats[collection] = {"vectors_count": 0, "status": "not_found"}
        return stats

    async def delete_collection(self, collection: str) -> None:
        """Delete a collection."""
        coll_name = f"{self._prefix}_{collection}"
        await self._client.delete_collection(coll_name)
        logger.info("Deleted collection", name=coll_name)
