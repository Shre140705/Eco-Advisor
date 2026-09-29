#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
: "${PORT:=3000}"
exec uvicorn backend.app:app --host 0.0.0.0 --port "$PORT"
