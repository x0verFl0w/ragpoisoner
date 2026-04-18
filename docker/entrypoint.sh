#!/bin/bash
set -e

echo "[*] ragpoisoner starting..."

MODEL="${OLLAMA_MODEL:-mistral}"
OLLAMA="${OLLAMA_HOST:-http://localhost:11434}"

echo "[*] Pulling Ollama model '${MODEL}' (may take a few minutes on first run)..."
curl -s -X POST "${OLLAMA}/api/pull" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"${MODEL}\"}" \
  --retry 5 --retry-delay 3 > /dev/null 2>&1 || true

echo "[+] Model ready. Launching ragpoisoner..."
exec ragpoisoner "$@"
