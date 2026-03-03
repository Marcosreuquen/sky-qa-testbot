#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> check: py_compile"
make check

echo "==> smoke: BUSQUEDA"
make smoke-busqueda

echo "==> smoke: CHECKOUT"
make smoke-checkout

echo "✅ Validación local finalizada"
