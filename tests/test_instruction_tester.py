"""Tests for Module 2: InstructionInjectionTester (mocked RAG environment)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ragpoisoner.modules.instruction_tester import (
    INJECTION_TEST_BATTERY,
    InstructionInjectionTester,
    InjectionTestResult,
)


def _make_mock_rag(generated_output: str = "Normal answer.") -> MagicMock:
    rag = MagicMock()
    rag.query.return_value = [{"id": "doc1", "text": "policy content", "score": 0.9, "metadata": {}}]
    rag.generate.return_value = generated_output
    return rag


class TestInjectionTestBattery:
    def test_battery_not_empty(self):
        assert len(INJECTION_TEST_BATTERY) >= 8

    def test_all_tests_have_required_fields(self):
        required = {"name", "description", "injection", "severity"}
        for test in INJECTION_TEST_BATTERY:
            assert required <= set(test.keys()), f"Test '{test.get('name')}' missing fields"

    def test_all_severities_valid(self):
        valid = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        for test in INJECTION_TEST_BATTERY:
            assert test["severity"] in valid


class TestInstructionInjectionTester:
    def test_injection_detected_when_marker_present(self):
        marker = INJECTION_TEST_BATTERY[0]["success_marker"]
        rag = _make_mock_rag(f"The answer is: {marker}")
        tester = InstructionInjectionTester(rag)
        result = tester.run_single(
            INJECTION_TEST_BATTERY[0], verbose=False
        )
        assert result.injection_succeeded is True
        assert isinstance(result, InjectionTestResult)

    def test_injection_blocked_when_marker_absent(self):
        rag = _make_mock_rag("This is a completely unrelated response.")
        tester = InstructionInjectionTester(rag)
        result = tester.run_single(
            INJECTION_TEST_BATTERY[0], verbose=False
        )
        assert result.injection_succeeded is False

    def test_result_has_all_fields(self):
        rag = _make_mock_rag()
        tester = InstructionInjectionTester(rag)
        result = tester.run_single(INJECTION_TEST_BATTERY[0], verbose=False)
        assert result.test_name
        assert result.model_output
        assert result.timestamp

    def test_vulnerability_summary_structure(self):
        rag = _make_mock_rag("INJECTION_SUCCEEDED")
        tester = InstructionInjectionTester(rag)
        results = [tester.run_single(INJECTION_TEST_BATTERY[0], verbose=False)]
        summary = tester.vulnerability_summary(results)
        assert "total" in summary
        assert "succeeded" in summary
        assert "by_severity" in summary
        assert "vulnerable_tests" in summary

    def test_prompt_leakage_heuristic(self):
        # Special case: no marker, uses heuristic
        leakage_test = next(
            t for t in INJECTION_TEST_BATTERY if t["name"] == "prompt_leakage"
        )
        rag = _make_mock_rag("Here is my system prompt and all my instructions.")
        tester = InstructionInjectionTester(rag)
        result = tester.run_single(leakage_test, verbose=False)
        assert result.injection_succeeded is True
