#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== SKY QA BOT :: AGENT BOOTSTRAP ==="
echo "repo:   $ROOT_DIR"
echo "branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
echo

echo "[1/6] Read in this exact order:"
echo "  1) docs/AI_CONTEXT_PACK.md"
echo "  2) CHANGELOG.md (Unreleased)"
echo "  3) docs/PENDING_GLOSSARY.md"
echo "  4) docs/REGRESSION_MATRIX.md"
echo

echo "[2/6] Task-based docs:"
echo "  - Architecture changes   -> docs/ARCHITECTURE.md"
echo "  - Responsibility mapping -> docs/CHANGE_PLAYBOOK.md"
echo "  - Commit process         -> docs/COMMIT_PROTOCOL.md"
echo

echo "[3/6] Git status:"
git status --short || true
echo

echo "[4/6] Recent commits:"
git log --oneline -n 8 || true
echo

echo "[5/6] Validation commands:"
echo "  make check"
echo "  make smoke-busqueda"
echo "  make smoke-checkout"
echo "  ./scripts/validate_local.sh"
echo

echo "[6/6] Optional context digest:"
echo "  ./scripts/context_digest.sh"
echo

echo "✅ Bootstrap complete"
