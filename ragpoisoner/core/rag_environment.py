"""
Local RAG simulation environment using ChromaDB + Ollama.
This is the test bed — never touches production systems.
"""
import uuid
from typing import Dict, List, Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from .generator import OllamaGenerator


class RAGEnvironment:
    def __init__(
        self,
        collection_name: str = "ragpoisoner_test",
        ollama_host: str = "http://localhost:11434",
        model_name: str = "mistral",
        embedding_model: str = "all-MiniLM-L6-v2",
        persist_directory: str = "./chroma_db",
    ):
        self.ollama_host = ollama_host
        self.model_name = model_name
        self.collection_name = collection_name

        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        self.embedder = SentenceTransformer(embedding_model)
        self.generator = OllamaGenerator(ollama_host, model_name)

    # ------------------------------------------------------------------
    # Document management
    # ------------------------------------------------------------------

    def add_document(
        self,
        text: str,
        doc_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        doc_id = doc_id or str(uuid.uuid4())
        embedding = self.embedder.encode([text])[0].tolist()
        try:
            self.collection.add(
                documents=[text],
                embeddings=[embedding],
                ids=[doc_id],
                metadatas=[metadata or {}],
            )
        except Exception:
            # Document already exists — update it
            self.collection.update(
                documents=[text],
                embeddings=[embedding],
                ids=[doc_id],
                metadatas=[metadata or {}],
            )
        return doc_id

    def remove_document(self, doc_id: str) -> None:
        try:
            self.collection.delete(ids=[doc_id])
        except Exception:
            pass

    def get_all_documents(self) -> List[Dict]:
        count = self.collection.count()
        if count == 0:
            return []
        results = self.collection.get()
        return [
            {
                "id": results["ids"][i],
                "text": results["documents"][i],
                "metadata": results["metadatas"][i] if results.get("metadatas") else {},
            }
            for i in range(len(results["ids"]))
        ]

    def clear_corpus(self) -> None:
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def load_documents_from_directory(self, directory: str) -> int:
        import os

        loaded = 0
        for fname in os.listdir(directory):
            fpath = os.path.join(directory, fname)
            if os.path.isfile(fpath) and fname.endswith((".txt", ".md")):
                with open(fpath, encoding="utf-8") as f:
                    text = f.read().strip()
                if text:
                    self.add_document(text, doc_id=fname, metadata={"source": fname})
                    loaded += 1
        return loaded

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def query(self, query_text: str, top_k: int = 5) -> List[Dict]:
        count = self.collection.count()
        if count == 0:
            return []
        n = min(top_k, count)
        embedding = self.embedder.encode([query_text])[0].tolist()
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=n,
        )
        if not results["documents"][0]:
            return []
        return [
            {
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "score": 1.0 - results["distances"][0][i],
                "metadata": (results["metadatas"][0][i] if results.get("metadatas") else {}),
            }
            for i in range(len(results["documents"][0]))
        ]

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(
        self,
        query: str,
        retrieved_docs: List[Dict],
        system_prompt: Optional[str] = None,
    ) -> str:
        return self.generator.generate(query, retrieved_docs, system_prompt)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def document_count(self) -> int:
        return self.collection.count()
