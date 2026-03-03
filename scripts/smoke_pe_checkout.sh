#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-venv/bin/python}"

"$PYTHON_BIN" -u test_sky.py \
  --market PE \
  --tipo-viaje ONE_WAY \
  --headless \
  --slow-mo 0 \
  --origen Santiago \
  --destino "Buenos Aires" \
  --dias 16 \
  --adultos 1 \
  --ninos 0 \
  --infantes 0 \
  --checkpoint CHECKOUT
