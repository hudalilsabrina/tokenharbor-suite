#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if command -v xvfb-run >/dev/null 2>&1; then
    exec xvfb-run -a .venv/bin/python main.py "$@"
else
    exec .venv/bin/python main.py "$@"
fi
