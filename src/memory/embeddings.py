from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_model_cache: dict[str, SentenceTransformer] = {}


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    if model_name not in _model_cache:
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model: %s", model_name)
        _model_cache[model_name] = SentenceTransformer(model_name)
    return _model_cache[model_name]


def encode_text(
    text: str,
    model_name: str = "all-MiniLM-L6-v2",
) -> np.ndarray:
    model = get_embedding_model(model_name)
    return model.encode(text, show_progress_bar=False)  # type: ignore[return-value]


def encode_batch(
    texts: list[str],
    model_name: str = "all-MiniLM-L6-v2",
    batch_size: int = 32,
) -> np.ndarray:
    model = get_embedding_model(model_name)
    return model.encode(texts, batch_size=batch_size, show_progress_bar=False)  # type: ignore[return-value]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class CachedEmbeddings:
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        maxsize: int = 1000,
        ttl: int = 3600,
    ) -> None:
        self._model_name = model_name
        self._maxsize = maxsize
        self._ttl = ttl
        self._cache: dict[int, tuple[np.ndarray, float]] = {}

    @property
    def cache_size(self) -> int:
        return len(self._cache)

    def encode(self, text: str) -> np.ndarray:
        cache_key = hash(text)
        now = time.monotonic()

        if cache_key in self._cache:
            embedding, timestamp = self._cache[cache_key]
            if now - timestamp < self._ttl:
                return embedding
            del self._cache[cache_key]

        embedding = encode_text(text, self._model_name)

        if len(self._cache) >= self._maxsize:
            self._evict_oldest()

        self._cache[cache_key] = (embedding, now)
        return embedding

    def encode_batch_cached(self, texts: list[str]) -> list[np.ndarray]:
        results: list[np.ndarray] = []
        uncached_texts: list[str] = []
        uncached_indices: list[int] = []
        now = time.monotonic()

        for i, text in enumerate(texts):
            cache_key = hash(text)
            if cache_key in self._cache:
                embedding, timestamp = self._cache[cache_key]
                if now - timestamp < self._ttl:
                    results.append(embedding)
                    continue
            results.append(np.array([]))
            uncached_texts.append(text)
            uncached_indices.append(i)

        if uncached_texts:
            embeddings = encode_batch(uncached_texts, self._model_name)
            for idx, text, embedding in zip(
                uncached_indices, uncached_texts, embeddings, strict=True
            ):
                cache_key = hash(text)
                if len(self._cache) >= self._maxsize:
                    self._evict_oldest()
                self._cache[cache_key] = (embedding, now)
                results[idx] = embedding

        return results

    def similarity(self, text_a: str, text_b: str) -> float:
        emb_a = self.encode(text_a)
        emb_b = self.encode(text_b)
        return cosine_similarity(emb_a, emb_b)

    def clear(self) -> None:
        self._cache.clear()

    def _evict_oldest(self) -> None:
        if not self._cache:
            return
        oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
        del self._cache[oldest_key]
