from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_chromadb_available = True
try:
    import chromadb
except ImportError:
    _chromadb_available = False


@dataclass(frozen=True)
class SearchResult:
    entry_id: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class LoreRetriever:
    def __init__(
        self,
        collection_name: str = "lore",
        embedding_model: str = "all-MiniLM-L6-v2",
    ) -> None:
        self._collection_name = collection_name
        self._embedding_model = embedding_model
        self._client: Any = None
        self._collection: Any = None
        self._indexed_count = 0

    @property
    def is_available(self) -> bool:
        return _chromadb_available

    @property
    def indexed_count(self) -> int:
        return self._indexed_count

    def initialize(self) -> bool:
        if not _chromadb_available:
            logger.warning("ChromaDB not available, RAG disabled")
            return False

        self._client = chromadb.Client()
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("LoreRetriever initialized (collection: %s)", self._collection_name)
        return True

    def index_entries(
        self,
        entries: list[dict[str, Any]],
    ) -> int:
        if not self._collection:
            logger.warning("Collection not initialized")
            return 0

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for entry in entries:
            entry_id = entry.get("id", "")
            content = entry.get("content", "")
            if not entry_id or not content:
                continue
            ids.append(entry_id)
            documents.append(content)
            metadatas.append(
                {
                    "name": entry.get("name", ""),
                    "category": entry.get("category", ""),
                    "priority": entry.get("priority", 0),
                }
            )

        if not ids:
            return 0

        self._collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        self._indexed_count = len(ids)
        logger.info("Indexed %d entries", self._indexed_count)
        return self._indexed_count

    def search(
        self,
        query: str,
        n_results: int = 10,
        category_filter: str | None = None,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        if not self._collection:
            return []

        where_filter: dict[str, Any] | None = None
        if category_filter:
            where_filter = {"category": category_filter}

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(n_results, self._indexed_count)
                if self._indexed_count > 0
                else n_results,
                where=where_filter,
            )
        except Exception:
            logger.exception("RAG search failed")
            return []

        search_results: list[SearchResult] = []
        if results and results["ids"] and results["ids"][0]:
            ids = results["ids"][0]
            distances = (
                results["distances"][0]
                if results.get("distances")
                else [0.0] * len(ids)
            )
            metadatas = (
                results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
            )

            for entry_id, distance, metadata in zip(
                ids, distances, metadatas, strict=False
            ):
                score = 1.0 - distance
                if score >= min_score:
                    search_results.append(
                        SearchResult(
                            entry_id=entry_id,
                            score=score,
                            metadata=metadata or {},
                        )
                    )

        return search_results

    def clear(self) -> None:
        if self._client and self._collection:
            self._client.delete_collection(self._collection_name)
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._indexed_count = 0
            logger.info("RAG index cleared")
