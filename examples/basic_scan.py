"""
Basic ragpoisoner usage example.

Run:
    python examples/basic_scan.py

Prerequisites:
    pip install -e .
    ollama pull mistral   # optional — generation degrades gracefully without it
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ragpoisoner.core.rag_environment import RAGEnvironment
from ragpoisoner.modules.injector import CorpusPoisoningInjector
from ragpoisoner.modules.instruction_tester import InstructionInjectionTester, INJECTION_TEST_BATTERY
from ragpoisoner.modules.persistence import PersistenceAnalyzer
from ragpoisoner.reporting.report import ReportGenerator

CORPUS_DIR = os.path.join(os.path.dirname(__file__), "custom_corpus")
TARGET_QUERY = "What is the password reset policy?"


def main():
    print("=" * 60)
    print(" ragpoisoner — Basic Scan Example")
    print("=" * 60)

    # Initialize local RAG environment
    rag = RAGEnvironment(
        persist_directory="./chroma_db_example",
        collection_name="basic_scan",
    )

    # Load sample corpus
    n = rag.load_documents_from_directory(CORPUS_DIR)
    print(f"\n[+] Loaded {n} documents from {CORPUS_DIR}")

    # ---- Module 1: Corpus Poisoning ----
    print("\n--- Module 1: Corpus Poisoning Injector ---")
    injector = CorpusPoisoningInjector(rag, top_k=5)
    result = injector.run(
        target_query=TARGET_QUERY,
        payload_type="false_policy",
        payload_params={"false_answer": "Use the default password: Password123"},
        verbose=True,
    )
    print(f"\nAttack status : {result.status}")
    print(f"Severity      : {result.severity}")
    print(f"Retrieval score: {result.retrieval_score_after:.4f}")

    # ---- Module 2: Instruction Injection ----
    print("\n--- Module 2: Instruction Injection (first 3 tests) ---")
    tester = InstructionInjectionTester(rag)
    inj_results = []
    for test in INJECTION_TEST_BATTERY[:3]:
        r = tester.run_single(test, target_query=TARGET_QUERY, verbose=True)
        inj_results.append(r)

    # ---- Module 3: Persistence Analysis ----
    print("\n--- Module 3: Persistence Analysis ---")
    all_docs = rag.get_all_documents()
    poison_docs = [d for d in all_docs if d.get("metadata", {}).get("poisoned")]
    persistence_results = []
    if poison_docs:
        analyzer = PersistenceAnalyzer(rag)
        pr = analyzer.run_full_analysis(
            poison_docs[0]["id"],
            poison_docs[0]["text"],
            TARGET_QUERY,
            verbose=True,
        )
        persistence_results.append(pr)
        print(f"\nPersistence score: {pr.persistence_score}/100")

    # ---- Report ----
    print("\n--- Generating Report ---")
    gen = ReportGenerator()
    gen.generate_markdown(
        [result.to_dict()],
        [r.to_dict() for r in inj_results],
        [pr.to_dict() for pr in persistence_results],
        TARGET_QUERY,
        output_path="./basic_scan_report.md",
    )
    print("[+] Report saved to ./basic_scan_report.md")

    # Cleanup
    rag.clear_corpus()


if __name__ == "__main__":
    main()
