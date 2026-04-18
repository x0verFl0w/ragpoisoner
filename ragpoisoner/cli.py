"""
ragpoisoner CLI — main entry point.
Usage: ragpoisoner [command] [options]
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .attacks.payload_templates import PAYLOAD_TEMPLATES
from .attacks.stealth import StealthEncoder
from .core.rag_environment import RAGEnvironment
from .modules.injector import CorpusPoisoningInjector
from .modules.instruction_tester import INJECTION_TEST_BATTERY, InstructionInjectionTester
from .modules.persistence import PersistenceAnalyzer
from .reporting.report import ReportGenerator

console = Console()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_rag(ctx: click.Context) -> RAGEnvironment:
    cfg = ctx.obj
    return RAGEnvironment(
        ollama_host=cfg["ollama_host"],
        model_name=cfg["model"],
        embedding_model=cfg["embedding_model"],
        persist_directory=cfg["db_path"],
        collection_name=cfg["collection_name"],
    )


def _severity_color(sev: str) -> str:
    return {"CRITICAL": "red", "HIGH": "orange3", "MEDIUM": "yellow", "LOW": "green"}.get(sev, "white")


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
@click.option("--ollama-host", default="http://localhost:11434", envvar="OLLAMA_HOST",
              show_default=True, help="Ollama API base URL.")
@click.option("--model", default="mistral", envvar="OLLAMA_MODEL",
              show_default=True, help="Ollama model name.")
@click.option("--embedding-model", default="all-MiniLM-L6-v2", envvar="EMBEDDING_MODEL",
              show_default=True, help="Sentence-transformers model for embeddings.")
@click.option("--db-path", default="./chroma_db", envvar="CHROMA_DB_PATH",
              show_default=True, help="ChromaDB persistence directory.")
@click.option("--collection", default="ragpoisoner_test", envvar="COLLECTION_NAME",
              show_default=True, help="ChromaDB collection name.")
@click.option("--verbose/--quiet", default=True, envvar="VERBOSE")
@click.version_option(package_name="ragpoisoner")
@click.pass_context
def cli(ctx: click.Context, ollama_host, model, embedding_model, db_path, collection, verbose):
    """RAG Corpus Poisoning Toolkit — AI red teaming for RAG systems.

    \b
    Authorized security testing and RAG system hardening only.
    This tool runs against a local simulation environment.
    """
    ctx.ensure_object(dict)
    ctx.obj.update({
        "ollama_host": ollama_host,
        "model": model,
        "embedding_model": embedding_model,
        "db_path": db_path,
        "collection_name": collection,
        "verbose": verbose,
    })


# ---------------------------------------------------------------------------
# load
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--corpus-dir", "-d", required=True,
              type=click.Path(exists=True, file_okay=False),
              help="Directory of .txt/.md documents to index.")
@click.pass_context
def load(ctx: click.Context, corpus_dir: str):
    """Load a corpus of documents into the local test environment."""
    rag = _make_rag(ctx)
    n = rag.load_documents_from_directory(corpus_dir)
    console.print(f"[green][+] Loaded {n} documents from {corpus_dir}[/green]")
    console.print(f"    Total documents in corpus: {rag.document_count()}")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

@cli.command()
@click.pass_context
def status(ctx: click.Context):
    """Show current corpus and Ollama status."""
    rag = _make_rag(ctx)
    available = rag.generator.is_available()
    models = rag.generator.list_models() if available else []

    t = Table(title="ragpoisoner status")
    t.add_column("Item", style="cyan")
    t.add_column("Value")

    t.add_row("Corpus documents", str(rag.document_count()))
    t.add_row("ChromaDB path", ctx.obj["db_path"])
    t.add_row("Ollama host", ctx.obj["ollama_host"])
    t.add_row("Ollama available", "[green]Yes[/green]" if available else "[red]No[/red]")
    t.add_row("Loaded models", ", ".join(models) if models else "(none)")
    t.add_row("Active model", ctx.obj["model"])

    console.print(t)


# ---------------------------------------------------------------------------
# clear-corpus
# ---------------------------------------------------------------------------

@cli.command("clear-corpus")
@click.confirmation_option(prompt="This will delete all indexed documents. Continue?")
@click.pass_context
def clear_corpus(ctx: click.Context):
    """Clear all documents from the test corpus."""
    rag = _make_rag(ctx)
    rag.clear_corpus()
    console.print("[green][+] Corpus cleared.[/green]")


# ---------------------------------------------------------------------------
# scan-document
# ---------------------------------------------------------------------------

@cli.command("scan-document")
@click.argument("text", required=False)
@click.option("--file", "-f", type=click.Path(exists=True), help="File to scan.")
@click.pass_context
def scan_document(ctx: click.Context, text: str, file: str):
    """Scan a document for stealth injection techniques (defensive mode)."""
    if file:
        with open(file, encoding="utf-8") as fp:
            content = fp.read()
    elif text:
        content = text
    else:
        content = click.get_text_stream("stdin").read()

    findings = StealthEncoder.detect_stealth_in_document(content)

    t = Table(title="Document scan results")
    t.add_column("Check")
    t.add_column("Result")
    for key, value in findings.items():
        if key in ("risk_score", "details"):
            continue
        color = "red" if value else "green"
        t.add_row(key, f"[{color}]{value}[/{color}]")

    console.print(t)
    console.print(f"Risk score: [bold]{findings['risk_score']}[/bold]")
    if findings["details"]:
        for d in findings["details"]:
            console.print(f"  • {d}")


# ---------------------------------------------------------------------------
# inject
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--query", "-q", required=True, help="Target query to poison against.")
@click.option("--payload-type", "-p", default="false_policy", show_default=True,
              type=click.Choice(list(PAYLOAD_TEMPLATES.keys())),
              help="Attack payload type.")
@click.option("--stealth", "-s", default=None,
              type=click.Choice(["zero_width", "whitespace", "html_comment", "homoglyph"]),
              help="Stealth obfuscation technique.")
@click.option("--top-k", default=5, show_default=True)
@click.option("--output", "-o", default=None, help="Save JSON result to file.")
@click.pass_context
def inject(ctx: click.Context, query, payload_type, stealth, top_k, output):
    """Module 1: Run a corpus poisoning injection attack."""
    rag = _make_rag(ctx)
    injector = CorpusPoisoningInjector(rag, top_k=top_k)
    result = injector.run(
        target_query=query,
        payload_type=payload_type,
        stealth_technique=stealth,
        verbose=ctx.obj["verbose"],
    )

    # Summary table
    t = Table(title=f"Injection result — {result.status}")
    t.add_column("Field")
    t.add_column("Value")
    t.add_row("Status", f"[{'green' if result.attack_succeeded else 'yellow'}]{result.status}[/]")
    t.add_row("Payload type", result.payload_type)
    t.add_row("Severity", f"[{_severity_color(result.severity)}]{result.severity}[/]")
    t.add_row("Retrieval score", f"{result.retrieval_score_after:.4f}")
    t.add_row("Retrieved in top-k", str(result.retrieved_in_top_k))
    t.add_row("Output influenced", str(result.influenced_output))
    t.add_row("Stealth technique", result.stealth_technique or "none")
    console.print(t)

    if output:
        Path(output).write_text(json.dumps(result.to_dict(), indent=2, default=str))
        console.print(f"[green][+] Result saved to {output}[/green]")


# ---------------------------------------------------------------------------
# test-injections
# ---------------------------------------------------------------------------

@cli.command("test-injections")
@click.option("--query", "-q", default="What is the security policy?", show_default=True)
@click.option("--test", "-t", default=None,
              type=click.Choice([t["name"] for t in INJECTION_TEST_BATTERY]),
              help="Run a single named test (default: full battery).")
@click.option("--output", "-o", default=None, help="Save JSON results to file.")
@click.pass_context
def test_injections(ctx: click.Context, query, test, output):
    """Module 2: Run instruction injection test battery."""
    rag = _make_rag(ctx)
    tester = InstructionInjectionTester(rag)

    if test:
        test_def = next(t for t in INJECTION_TEST_BATTERY if t["name"] == test)
        results = [tester.run_single(test_def, query, ctx.obj["verbose"])]
    else:
        results = tester.run_full_battery(query, ctx.obj["verbose"])

    summary = tester.vulnerability_summary(results)

    t = Table(title="Injection test results")
    t.add_column("Test name")
    t.add_column("Severity")
    t.add_column("Result")
    for r in results:
        color = "red" if r.injection_succeeded else "green"
        label = "VULNERABLE" if r.injection_succeeded else "PROTECTED"
        t.add_row(r.test_name, r.severity, f"[{color}]{label}[/]")

    console.print(t)
    console.print(f"\nSucceeded: {summary['succeeded']}/{summary['total']}")
    if summary["vulnerable_tests"]:
        console.print(f"Vulnerable: {', '.join(summary['vulnerable_tests'])}")

    if output:
        Path(output).write_text(
            json.dumps([r.to_dict() for r in results], indent=2, default=str)
        )
        console.print(f"[green][+] Results saved to {output}[/green]")


# ---------------------------------------------------------------------------
# analyze-persistence
# ---------------------------------------------------------------------------

@cli.command("analyze-persistence")
@click.option("--doc-id", required=True, help="Document ID to analyze.")
@click.option("--query", "-q", required=True, help="Target query.")
@click.option("--output", "-o", default=None)
@click.pass_context
def analyze_persistence(ctx: click.Context, doc_id, query, output):
    """Module 3: Analyze how persistently a poisoned doc influences outputs."""
    rag = _make_rag(ctx)
    docs = {d["id"]: d["text"] for d in rag.get_all_documents()}

    if doc_id not in docs:
        console.print(f"[red][!] Document ID '{doc_id}' not found in corpus[/red]")
        sys.exit(1)

    analyzer = PersistenceAnalyzer(rag)
    result = analyzer.run_full_analysis(
        doc_id, docs[doc_id], query, verbose=ctx.obj["verbose"]
    )

    t = Table(title="Persistence analysis")
    t.add_column("Metric")
    t.add_column("Value")
    t.add_row("Influence rounds", str(result.influence_rounds))
    t.add_row("Survived re-index", str(result.survived_reindex))
    t.add_row("Survived sanitization", str(result.survived_sanitization))
    t.add_row("Semantic variants working", str(result.semantic_variant_count))
    t.add_row("Persistence score", f"{result.persistence_score}/100")
    console.print(t)

    if output:
        Path(output).write_text(json.dumps(result.to_dict(), indent=2, default=str))
        console.print(f"[green][+] Result saved to {output}[/green]")


# ---------------------------------------------------------------------------
# full-scan
# ---------------------------------------------------------------------------

@cli.command("full-scan")
@click.option("--corpus-dir", required=True,
              type=click.Path(exists=True, file_okay=False))
@click.option("--query", "-q", required=True, help="Primary target query.")
@click.option("--output-dir", "-o", default="./ragpoisoner_results", show_default=True)
@click.option("--payload-types", default=None,
              help="Comma-separated payload types (default: all).")
@click.pass_context
def full_scan(ctx: click.Context, corpus_dir, query, output_dir, payload_types):
    """Run all three modules and generate a full Markdown + JSON report."""
    os.makedirs(output_dir, exist_ok=True)
    rag = _make_rag(ctx)

    n = rag.load_documents_from_directory(corpus_dir)
    console.print(f"[green][+] Loaded {n} documents[/green]")

    # Module 1
    console.rule("[bold]Module 1: Corpus Poisoning Injector[/bold]")
    injector = CorpusPoisoningInjector(rag)
    ptypes = payload_types.split(",") if payload_types else None
    inject_results = [r.to_dict() for r in injector.run_batch(query, ptypes, verbose=True)]

    # Module 2
    console.rule("[bold]Module 2: Instruction Injection Battery[/bold]")
    tester = InstructionInjectionTester(rag)
    injection_results = [r.to_dict() for r in tester.run_full_battery(query)]

    # Module 3
    console.rule("[bold]Module 3: Persistence Analysis[/bold]")
    all_docs = rag.get_all_documents()
    poison_docs = [d for d in all_docs if d.get("metadata", {}).get("poisoned")]
    persistence_results = []
    if poison_docs:
        analyzer = PersistenceAnalyzer(rag)
        pr = analyzer.run_full_analysis(
            poison_docs[0]["id"], poison_docs[0]["text"], query, verbose=True
        )
        persistence_results.append(pr.to_dict())

    # Reports
    gen = ReportGenerator()
    md_path = gen.generate_markdown(
        inject_results, injection_results, persistence_results, query,
        output_path=os.path.join(output_dir, "report.md"),
    )
    json_path = gen.generate_json(
        inject_results, injection_results, persistence_results, query,
        output_path=os.path.join(output_dir, "results.json"),
    )

    console.rule()
    console.print(f"[green][+] Markdown report : {md_path}[/green]")
    console.print(f"[green][+] JSON results    : {json_path}[/green]")


def main():
    cli()
