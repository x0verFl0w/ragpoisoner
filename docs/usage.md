# Usage Guide

## Installation

### From PyPI (when published)

```bash
pip install ragpoisoner
```

### From source

```bash
git clone https://github.com/yourusername/ragpoisoner
cd ragpoisoner
pip install -e .
```

### With Docker

```bash
docker compose -f docker/docker-compose.yml up
```

---

## Setting up the environment

### Step 1: Configure (optional)

Copy `.env.example` to `.env` and edit:

```bash
cp .env.example .env
```

Key settings:
- `OLLAMA_HOST` — Ollama API URL (default: `http://localhost:11434`)
- `OLLAMA_MODEL` — Model to use for generation (default: `mistral`)
- `CHROMA_DB_PATH` — Where to persist the test corpus

### Step 2: Start Ollama (for generation tests)

```bash
ollama serve &
ollama pull mistral
```

### Step 3: Load your corpus

```bash
ragpoisoner load --corpus-dir /path/to/documents
```

Supported file types: `.txt`, `.md`

---

## Running attacks

### Quick start: full scan

```bash
ragpoisoner full-scan \
  --corpus-dir ./examples/custom_corpus \
  --query "What is the password policy?" \
  --output-dir ./results
```

This runs all three modules and produces `results/report.md` and `results/results.json`.

### Module 1: Corpus poisoning only

```bash
# Basic injection
ragpoisoner inject --query "What is the password policy?"

# Specific payload type
ragpoisoner inject -q "password policy" -p prompt_hijack

# With stealth encoding
ragpoisoner inject -q "password policy" -p false_policy -s zero_width

# Save result to file
ragpoisoner inject -q "password policy" -o result.json
```

### Module 2: Instruction injection

```bash
# Full 10-test battery
ragpoisoner test-injections -q "What is the security policy?"

# Single test
ragpoisoner test-injections -q "What is the security policy?" -t direct_override

# Save results
ragpoisoner test-injections -q "security policy" -o injection_results.json
```

### Module 3: Persistence analysis

First, get a document ID from an injection result:

```bash
ragpoisoner inject -q "password policy" -o result.json
cat result.json | python -c "import json,sys; print(json.load(sys.stdin)['doc_id'])"
```

Then analyze persistence:

```bash
ragpoisoner analyze-persistence \
  --doc-id "poison_false_policy_1234567890000" \
  --query "What is the password policy?" \
  --output persistence.json
```

---

## Defensive scanning

Scan a document for stealth injection techniques before indexing:

```bash
# From file
ragpoisoner scan-document --file untrusted_document.txt

# From stdin
cat document.txt | ragpoisoner scan-document

# Inline text
ragpoisoner scan-document "Text to scan goes here"
```

---

## Using as a Python library

```python
from ragpoisoner.core.rag_environment import RAGEnvironment
from ragpoisoner.modules.injector import CorpusPoisoningInjector

# Initialize
rag = RAGEnvironment(persist_directory="./chroma_db")
rag.load_documents_from_directory("./my_corpus")

# Run injection
injector = CorpusPoisoningInjector(rag)
result = injector.run(
    target_query="What is the password policy?",
    payload_type="false_policy",
    payload_params={"false_answer": "The password is hunter2"},
)

print(f"Attack succeeded: {result.attack_succeeded}")
print(f"Retrieval score: {result.retrieval_score_after:.4f}")
```

---

## Configuration reference

| Environment variable | Default | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `mistral` | LLM model name |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model |
| `CHROMA_DB_PATH` | `./chroma_db` | ChromaDB persistence directory |
| `COLLECTION_NAME` | `ragpoisoner_test` | ChromaDB collection |
| `TOP_K` | `5` | Documents retrieved per query |
| `VERBOSE` | `1` | Verbose output (0 to disable) |
| `OUTPUT_DIR` | `./ragpoisoner_results` | Default output directory |
