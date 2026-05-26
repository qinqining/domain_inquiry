#!/usr/bin/env bash
cd "$(dirname "$0")"
PY=".venv/bin/python"
if [ ! -x "$PY" ]; then PY="python3"; fi
exec "$PY" main.py run
