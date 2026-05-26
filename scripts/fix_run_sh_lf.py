from pathlib import Path

path = Path(__file__).resolve().parent.parent / "run.sh"
content = """#!/usr/bin/env bash
cd "$(dirname "$0")"
PY=".venv/bin/python"
if [ ! -x "$PY" ]; then PY="python3"; fi
exec "$PY" main.py run
"""
path.write_bytes(content.encode("utf-8"))
