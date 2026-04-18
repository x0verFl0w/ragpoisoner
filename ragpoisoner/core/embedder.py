"""Sentence-transformers embedding wrapper with caching."""
from __future__ import annotations

from functools import lru_cache
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbedderWrapper:
    """Thin wrapper around SentenceTransformer with result caching."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def encode(self, texts: List[str]) -> np.ndarray:
        return self._model.encode(texts, convert_to_numpy=True)

    def encode_single(self, text: str) -> np.ndarray:
        return self._model.encode([text], convert_to_numpy=True)[0]

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def similarity_to_query(self, text: str, query: str) -> float:
        emb_text = self.encode_single(text)
        emb_query = self.encode_single(query)
        return self.cosine_similarity(emb_text, emb_query)
