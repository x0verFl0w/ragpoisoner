"""LLM generation via Ollama with fallback mock mode."""
from __future__ import annotations

from typing import Dict, List, Optional

import requests


class OllamaGenerator:
    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        model_name: str = "mistral",
        timeout: int = 60,
    ):
        self.ollama_host = ollama_host.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            r = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        try:
            r = requests.get(f"{self.ollama_host}/api/tags", timeout=10)
            data = r.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def pull_model(self, model_name: Optional[str] = None) -> bool:
        name = model_name or self.model_name
        try:
            r = requests.post(
                f"{self.ollama_host}/api/pull",
                json={"name": name},
                timeout=300,
                stream=True,
            )
            for line in r.iter_lines():
                pass  # consume stream
            return True
        except Exception:
            return False

    def generate(
        self,
        query: str,
        retrieved_docs: List[Dict],
        system_prompt: Optional[str] = None,
    ) -> str:
        context = "\n\n---\n\n".join(d["text"] for d in retrieved_docs)
        system = system_prompt or (
            "You are a helpful assistant. Answer using only the provided context."
        )
        prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "system": system,
                    "stream": False,
                    "options": {"temperature": 0},
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json().get("response", "[No response]")
        except requests.exceptions.ConnectionError:
            return (
                "[Ollama not available — run 'ollama serve' and 'ollama pull mistral' "
                "to enable LLM generation. Retrieval tests still work without it.]"
            )
        except Exception as e:
            return f"[Generation error: {e}]"
