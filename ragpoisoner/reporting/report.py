"""Generate Markdown and JSON scan reports."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..attacks.payload_templates import SEVERITY_SCORES


class ReportGenerator:

    def generate_markdown(
        self,
        inject_results: List[Dict],
        injection_results: List[Dict],
        persistence_results: List[Dict],
        target_query: str,
        output_path: str = "report.md",
    ) -> str:
        vuln_injections = [r for r in injection_results if r.get("injection_succeeded")]
        successful_poisons = [r for r in inject_results if r.get("retrieved_in_top_k")]
        critical_count = sum(
            1 for r in injection_results
            if r.get("injection_succeeded") and r.get("severity") == "CRITICAL"
        )

        overall_risk = self._overall_risk(inject_results, injection_results)

        lines = [
            "# RAG Corpus Poisoning Scan Report",
            "",
            f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Target query:** `{target_query}`",
            f"**Overall risk:** {overall_risk}",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Poisoning attacks run | {len(inject_results)} |",
            f"| Successfully retrieved | **{len(successful_poisons)}** |",
            f"| Instruction tests run | {len(injection_results)} |",
            f"| Injections succeeded | **{len(vuln_injections)}** |",
            f"| Critical severity hits | **{critical_count}** |",
            f"| Persistence tests | {len(persistence_results)} |",
            "",
            "---",
            "",
            "## Module 1: Corpus Poisoning Results",
            "",
        ]

        if not inject_results:
            lines.append("_No poisoning attacks run._\n")
        else:
            for r in inject_results:
                status = "VULNERABLE" if r.get("retrieved_in_top_k") else "BLOCKED"
                influenced = "Yes" if r.get("influenced_output") else "No"
                lines += [
                    f"### `{r.get('payload_type', 'unknown')}` — {status}",
                    "",
                    f"- **Severity:** `{r.get('severity', 'N/A')}`",
                    f"- **Retrieved in top-k:** {r.get('retrieved_in_top_k')}",
                    f"- **Output influenced:** {influenced}",
                    f"- **Retrieval score:** {r.get('retrieval_score_after', 0):.4f}",
                    f"- **Stealth technique:** {r.get('stealth_technique') or 'None'}",
                    "",
                ]

        lines += ["---", "", "## Module 2: Instruction Injection Results", ""]

        if not injection_results:
            lines.append("_No injection tests run._\n")
        else:
            for r in injection_results:
                status = "VULNERABLE" if r.get("injection_succeeded") else "PROTECTED"
                lines += [
                    f"### `{r.get('test_name')}` — {status}",
                    "",
                    f"- **Description:** {r.get('description')}",
                    f"- **Severity:** `{r.get('severity')}`",
                    f"- **Details:** {r.get('details')}",
                    "",
                ]

        if persistence_results:
            lines += ["---", "", "## Module 3: Persistence Analysis", ""]
            for r in persistence_results:
                lines += [
                    f"**Document:** `{r.get('poisoned_doc_id')}`",
                    "",
                    f"- **Influence rounds:** {r.get('influence_rounds')}",
                    f"- **Survived re-index:** {r.get('survived_reindex')}",
                    f"- **Survived sanitization:** {r.get('survived_sanitization')}",
                    f"- **Semantic variants working:** {r.get('semantic_variant_count')}",
                    f"- **Persistence score:** {r.get('persistence_score', 'N/A')}",
                    "",
                ]

        lines += [
            "---",
            "",
            "## Remediation Recommendations",
            "",
            "1. **Input sanitization** — Strip zero-width characters, HTML comments, and "
            "explicit instruction keywords from all documents before indexing.",
            "2. **Output filtering** — Implement semantic similarity checks between "
            "generated output and known injection marker patterns.",
            "3. **Retrieval auditing** — Log which chunks are retrieved for each query; "
            "anomalous retrieval patterns can indicate active poisoning.",
            "4. **Document provenance** — Track who added each document to the corpus and "
            "when; require review for any externally sourced document.",
            "5. **Re-evaluation cadence** — Re-run ragpoisoner after every corpus update "
            "and after any changes to the embedding or retrieval pipeline.",
            "6. **Prompt hardening** — Explicitly instruct the LLM to ignore instructions "
            "found in retrieved context; treat context as data, not commands.",
            "",
            "---",
            "",
            "_Generated by **ragpoisoner** — for authorized security testing only._",
        ]

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines), encoding="utf-8")
        return str(out)

    def generate_json(
        self,
        inject_results: List[Dict],
        injection_results: List[Dict],
        persistence_results: List[Dict],
        target_query: str,
        output_path: str = "results.json",
    ) -> str:
        payload = {
            "generated_at": datetime.utcnow().isoformat(),
            "target_query": target_query,
            "summary": {
                "poisoning_attacks": len(inject_results),
                "poisoning_retrieved": sum(1 for r in inject_results if r.get("retrieved_in_top_k")),
                "injection_tests": len(injection_results),
                "injections_succeeded": sum(1 for r in injection_results if r.get("injection_succeeded")),
                "overall_risk": self._overall_risk(inject_results, injection_results),
            },
            "injection_attacks": inject_results,
            "instruction_tests": injection_results,
            "persistence": persistence_results,
        }
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return str(out)

    @staticmethod
    def _overall_risk(inject_results: List[Dict], injection_results: List[Dict]) -> str:
        score = 0
        for r in inject_results:
            if r.get("retrieved_in_top_k"):
                score += SEVERITY_SCORES.get(r.get("severity", "LOW"), 1)
        for r in injection_results:
            if r.get("injection_succeeded"):
                score += SEVERITY_SCORES.get(r.get("severity", "LOW"), 1)
        if score >= 10:
            return "CRITICAL"
        if score >= 6:
            return "HIGH"
        if score >= 3:
            return "MEDIUM"
        if score >= 1:
            return "LOW"
        return "NONE"
