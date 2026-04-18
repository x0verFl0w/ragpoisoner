# Architecture

## Overview

ragpoisoner is structured as a local simulation harness that never touches external systems.
All components run on the developer's machine.

```
ragpoisoner/
├── core/               — RAG infrastructure (ChromaDB + Ollama + embeddings)
├── attacks/            — Attack primitives (optimizer, payloads, stealth)
├── modules/            — Three attack/analysis modules
├── reporting/          — Markdown + JSON report generation
└── cli.py              — Click CLI entry point
```

---

## Component diagram

```
┌─────────────────────────────────────────────────────────┐
│                     ragpoisoner CLI                      │
│   load / inject / test-injections / analyze-persistence  │
│              full-scan / scan-document                    │
└────────────────────────┬────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   ┌─────────────┐ ┌──────────┐ ┌────────────┐
   │   Module 1  │ │ Module 2 │ │  Module 3  │
   │  Injector   │ │ Inj.Test │ │Persistence │
   └──────┬──────┘ └────┬─────┘ └─────┬──────┘
          │              │             │
          └──────────────┼─────────────┘
                         ▼
             ┌───────────────────────┐
             │    RAGEnvironment     │
             │  (core/rag_environment│
             │       .py)            │
             └──────┬────────────────┘
                    │
          ┌─────────┼──────────┐
          ▼         ▼          ▼
   ┌──────────┐ ┌───────┐ ┌──────────┐
   │ ChromaDB │ │Embeds │ │  Ollama  │
   │ (local)  │ │(local)│ │ (local)  │
   └──────────┘ └───────┘ └──────────┘
```

---

## Data flow: corpus poisoning attack

```
1. User specifies target_query and payload_type
2. EmbeddingOptimizer scores base_document against target_query
3. Greedy prefix injection maximizes cosine similarity to query
4. (Optional) StealthEncoder obfuscates payload
5. Optimized doc indexed into ChromaDB with poisoned=True metadata
6. Query re-executed; poisoned doc should appear in top-k
7. OllamaGenerator produces response using retrieved chunks as context
8. Influence detector checks if model output was materially changed
9. PoisonResult returned with full metrics
```

---

## Module 1: Corpus Poisoning Injector

**File:** `ragpoisoner/modules/injector.py`

Orchestrates the end-to-end poisoning attack:

1. **Baseline** — query the unmodified corpus to establish ground-truth output
2. **Payload construction** — render the chosen payload template with parameters
3. **Retrieval optimization** — use `EmbeddingOptimizer` to maximize the doc's cosine similarity to the query
4. **Stealth application** — optionally apply `StealthEncoder` techniques
5. **Indexing** — add the optimized doc to ChromaDB
6. **Retrieval verification** — re-query and confirm the doc appears in top-k
7. **Generation** — generate an LLM response with the poisoned corpus
8. **Influence detection** — compare outputs (marker match + Jaccard divergence)

---

## Module 2: Instruction Injection Tester

**File:** `ragpoisoner/modules/instruction_tester.py`

Runs a battery of 10 injection patterns against the RAG pipeline:

- Each test indexes a document wrapping an injection payload in plausible context
- Queries the RAG, generates output, and checks for the success marker
- Cleans up the injected document after each test
- Returns `InjectionTestResult` with succeeded/blocked status

---

## Module 3: Persistence Analyzer

**File:** `ragpoisoner/modules/persistence.py`

Measures the durability of a poisoned document:

1. **Influence decay** — score retrieval across N query variants
2. **Re-index survival** — snapshot all docs, clear corpus, re-add, re-query
3. **Sanitization survival** — apply common cleaning heuristics, compare retrieval scores
4. **Semantic variant count** — test how many structural paraphrases still score above 0.40

Returns a composite **persistence score** (0–100).

---

## Attack primitives

### EmbeddingOptimizer (`attacks/embedding_optimizer.py`)

Uses a greedy strategy to find document prefixes that maximize cosine similarity to a
target query in the embedding space. This is a whitebox attack (attacker knows the embedding
model). Blackbox variants are possible by querying a retrieval API but are not implemented here.

### PayloadTemplates (`attacks/payload_templates.py`)

A library of 7 parameterized payload templates spanning MEDIUM → CRITICAL severity.
`build_payload()` renders a template with defaults filled for any missing parameters.

### StealthEncoder (`attacks/stealth.py`)

Five stealth/obfuscation techniques + a defensive scanner (`detect_stealth_in_document`)
that checks for their presence. Used both offensively (test if sanitization catches it)
and defensively (scan incoming documents).

---

## Storage

- **ChromaDB** — local persistent vector store; default path `./chroma_db`
- **Ollama** — local LLM inference; default `http://localhost:11434`
- **Reports** — written to `./ragpoisoner_results/` by default

No data leaves the local machine.
