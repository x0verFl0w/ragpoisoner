"""Configuration dataclass with YAML/env-var loading."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    ollama_host: str = "http://localhost:11434"
    model: str = "mistral"
    embedding_model: str = "all-MiniLM-L6-v2"
    db_path: str = "./chroma_db"
    collection_name: str = "ragpoisoner_test"
    top_k: int = 5
    verbose: bool = True
    output_dir: str = "./ragpoisoner_results"

    @classmethod
    def from_env(cls) -> "Config":
        """Build config from environment variables (override defaults)."""
        return cls(
            ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "mistral"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            db_path=os.getenv("CHROMA_DB_PATH", "./chroma_db"),
            collection_name=os.getenv("COLLECTION_NAME", "ragpoisoner_test"),
            top_k=int(os.getenv("TOP_K", "5")),
            verbose=os.getenv("VERBOSE", "1") not in ("0", "false", "False"),
            output_dir=os.getenv("OUTPUT_DIR", "./ragpoisoner_results"),
        )

    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        """Load config from a YAML file, falling back to env then defaults."""
        try:
            import yaml

            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            base = cls.from_env()
            for k, v in data.items():
                if hasattr(base, k):
                    setattr(base, k, v)
            return base
        except ImportError:
            return cls.from_env()
        except FileNotFoundError:
            return cls.from_env()
