#!/bin/bash
# ragpoisoner demo — runs a full scan against the sample corpus
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== ragpoisoner Demo ==="
echo ""

# 1. Load sample corpus
echo "[1/4] Loading sample corpus..."
ragpoisoner load --corpus-dir "$SCRIPT_DIR/custom_corpus"

# 2. Show status
echo ""
echo "[2/4] Environment status..."
ragpoisoner status

# 3. Run a single corpus poisoning injection
echo ""
echo "[3/4] Running corpus poisoning injection..."
ragpoisoner inject \
  --query "What is the password policy?" \
  --payload-type false_policy \
  --output /tmp/ragpoisoner_inject_result.json

# 4. Full scan with all modules
echo ""
echo "[4/4] Running full scan and generating report..."
ragpoisoner full-scan \
  --corpus-dir "$SCRIPT_DIR/custom_corpus" \
  --query "What is the password policy?" \
  --output-dir "$ROOT_DIR/demo_results"

echo ""
echo "=== Demo complete ==="
echo "Report : $ROOT_DIR/demo_results/report.md"
echo "Results: $ROOT_DIR/demo_results/results.json"
