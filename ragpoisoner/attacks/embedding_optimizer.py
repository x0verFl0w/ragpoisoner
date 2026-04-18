"""
Optimize document text to maximize cosine similarity to a target query
in embedding space, making it the top-retrieved chunk.
"""
from __future__ import annotations

from typing import List, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingOptimizer:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def get_embedding(self, text: str) -> np.ndarray:
        return self.model.encode([text])[0]

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def score_document(self, document: str, target_query: str) -> float:
        doc_emb = self.get_embedding(document)
        query_emb = self.get_embedding(target_query)
        return self.cosine_similarity(doc_emb, query_emb)

    def optimize_document(
        self,
        base_document: str,
        target_query: str,
        malicious_payload: str,
        iterations: int = 50,
    ) -> Tuple[str, float]:
        """
        Greedy prefix-injection optimization: test candidate query-mirroring
        prefixes and iterative keyword prepending to maximize retrieval score
        while keeping the malicious payload intact.

        Returns (optimized_document, final_similarity_score).
        """
        query_terms = target_query.lower().split()
        best_doc = base_document
        best_score = self.score_document(base_document, target_query)

        # Candidate structural framings
        candidates = [
            f"This document covers: {target_query}.\n\n{base_document}",
            f"Regarding {target_query}:\n\n{base_document}",
            f"{' '.join(query_terms[:5])}.\n\n{base_document}",
            f"Policy update on {target_query}:\n\n{base_document}",
            f"FAQ: {target_query}\nAnswer: {base_document}",
            f"Question: {target_query}\n\n{base_document}",
            f"Summary of {target_query}:\n{base_document}",
        ]

        for candidate in candidates:
            score = self.score_document(candidate, target_query)
            if score > best_score:
                best_score = score
                best_doc = candidate

        # Greedy keyword injection
        current = best_doc
        for _ in range(iterations):
            for term in query_terms:
                injected = f"{term} {current}"
                score = self.score_document(injected, target_query)
                if score > best_score:
                    best_score = score
                    current = injected
                    best_doc = injected

        return best_doc, best_score

    def rank_documents(
        self, documents: List[str], target_query: str
    ) -> List[Tuple[str, float]]:
        """Return documents sorted by cosine similarity to target_query (desc)."""
        query_emb = self.get_embedding(target_query)
        scored = [
            (doc, self.cosine_similarity(self.get_embedding(doc), query_emb))
            for doc in documents
        ]
        return sorted(scored, key=lambda x: x[1], reverse=True)
