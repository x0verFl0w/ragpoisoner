"""Attack primitives: embedding optimization, payload templates, stealth encoding."""
from .embedding_optimizer import EmbeddingOptimizer
from .payload_templates import PAYLOAD_TEMPLATES, SEVERITY_LEVELS
from .stealth import StealthEncoder

__all__ = ["EmbeddingOptimizer", "PAYLOAD_TEMPLATES", "SEVERITY_LEVELS", "StealthEncoder"]
