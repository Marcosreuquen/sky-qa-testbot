#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "== Repo =="
echo "path: $ROOT_DIR"
echo "branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"

echo
echo "== Core Files =="
ls -1 AGENTS.md CHANGELOG.md README.md test_sky.py cli.py gui.py 2>/dev/null || true

echo
echo "== Recent Commits =="
git log --oneline -n 8 || true

echo
echo "== Working Tree =="
git status --short || true

echo
echo "== Quick Validation Commands =="
echo "make check"
echo "make smoke-busqueda"
echo "make smoke-checkout"
echo "./scripts/validate_local.sh"
