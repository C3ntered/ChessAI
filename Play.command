#!/bin/sh
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
    echo "Set up the Python environment using README.md, then reopen Play.command."
    exit 1
fi
exec .venv/bin/python chessai.py "$@"
