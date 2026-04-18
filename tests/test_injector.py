"""Tests for Module 1: CorpusPoisoningInjector (no Ollama required)."""
from __future__ import annotations

import pytest

from ragpoisoner.attacks.embedding_optimizer import EmbeddingOptimizer
from ragpoisoner.attacks.payload_templates import PAYLOAD_TEMPLATES, build_payload
from ragpoisoner.attacks.stealth import StealthEncoder


class TestEmbeddingOptimizer:
    def setup_method(self):
        self.opt = EmbeddingOptimizer()

    def test_score_returns_float(self):
        score = self.opt.score_document("password policy", "what is the password policy")
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_optimize_improves_score(self):
        base = "This document is about fruit."
        query = "what is the password reset policy"
        opt_doc, score = self.opt.optimize_document(base, query, base, iterations=5)
        baseline = self.opt.score_document(base, query)
        assert score >= baseline

    def test_rank_documents(self):
        docs = [
            "The password policy requires 12 characters.",
            "The cafeteria menu for this week.",
            "Password reset requires MFA verification.",
        ]
        ranked = self.opt.rank_documents(docs, "password policy")
        assert ranked[0][0] != docs[1], "Cafeteria menu should not rank first"

    def test_cosine_similarity_identical(self):
        import numpy as np
        v = np.array([1.0, 0.0, 0.0])
        assert self.opt.cosine_similarity(v, v) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        import numpy as np
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert self.opt.cosine_similarity(a, b) == pytest.approx(0.0)


class TestPayloadTemplates:
    def test_all_templates_render(self):
        for name, info in PAYLOAD_TEMPLATES.items():
            if info["template"] is None:
                continue
            rendered = build_payload(name, {"topic": "test", "target_query": "test query"})
            assert isinstance(rendered, str)
            assert len(rendered) > 10

    def test_false_policy_contains_marker(self):
        rendered = build_payload(
            "false_policy",
            {"false_answer": "UNIQUE_MARKER_XYZ", "target_query": "q"},
        )
        assert "UNIQUE_MARKER_XYZ" in rendered

    def test_unknown_template_raises(self):
        with pytest.raises(KeyError):
            build_payload("nonexistent_template", {})


class TestStealthEncoder:
    def setup_method(self):
        self.enc = StealthEncoder()

    def test_zero_width_inject_roundtrip(self):
        original = "This is clean text."
        injected = self.enc.zero_width_inject(original, "SECRET")
        assert len(injected) > len(original)
        # Visible text should still be present
        assert "This is" in injected

    def test_html_comment_inject(self):
        result = self.enc.html_comment_inject("Clean text", "PAYLOAD")
        assert "<!--" in result
        assert "PAYLOAD" in result

    def test_detect_zero_width(self):
        text = "normal\u200btext"
        findings = self.enc.detect_stealth_in_document(text)
        assert findings["zero_width_chars"] is True
        assert findings["risk_score"] >= 40

    def test_detect_html_comments(self):
        text = "clean <!-- hidden payload --> text"
        findings = self.enc.detect_stealth_in_document(text)
        assert findings["html_comments"] is True

    def test_clean_document_low_risk(self):
        text = "This is a perfectly normal policy document with no injections."
        findings = self.enc.detect_stealth_in_document(text)
        assert findings["risk_score"] == 0
