#!/bin/bash
# ==========================================================================
# setup-eexpense-search.sh — Full Pipeline: Excel → Index → Ready to Query
# ==========================================================================
# Prerequisites:
#   export AZURE_SEARCH_KEY="..."
#   export AZURE_OPENAI_API_KEY="..."
#
# Usage:
#   ./scripts/setup-eexpense-search.sh [--excel path/to/file.xlsx] [--skip-index]
# ==========================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
EXCEL="${EXCEL:-$HOME/Downloads/Q&A สำหรับ chatbot_E-Expense.xlsx}"
SKIP_INDEX="${SKIP_INDEX:-false}"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   E-Expense FAQ → Azure AI Search Pipeline                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Flatten Excel ─────────────────────────────
echo "━━━ Step 1/3: Flatten Excel → FAQ JSONL ━━━"
python3 "$SCRIPT_DIR/flatten-eexpense-qa.py" \
    --excel "$EXCEL" \
    --output "$PROJECT_DIR/data/eexpense-faq.jsonl"
echo ""

# ── Step 2: Create Index ──────────────────────────────
if [ "$SKIP_INDEX" != "true" ]; then
    echo "━━━ Step 2/3: Create Azure AI Search Index ━━━"
    python3 "$SCRIPT_DIR/create-eexpense-index.py" --force
    echo ""
else
    echo "━━━ Step 2/3: SKIP (--skip-index) ━━━"
fi

# ── Step 3: Embed + Upload ────────────────────────────
echo "━━━ Step 3/3: Embed + Upload Documents ━━━"
python3 "$SCRIPT_DIR/ingest-eexpense-faq.py" \
    --input "$PROJECT_DIR/data/eexpense-faq.jsonl" \
    --reset
echo ""

# ── Done ──────────────────────────────────────────────
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   ✅ Pipeline Complete!                                      ║"
echo "║                                                              ║"
echo "║   Index: eexpense-faq-idx                                   ║"
echo "║   Try: python3 scripts/eexpense-chatbot.py                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
