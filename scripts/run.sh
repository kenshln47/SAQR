#!/bin/sh
# Linux and macOS. The server binds to 127.0.0.1 only.
set -eu
cd "$(dirname "$0")/.."

if [ ! -x .venv/bin/python ]; then
  echo "First run: scripts/setup.sh" >&2
  exit 1
fi

: "${SAQR_PORT:=8765}"
export SAQR_PORT
exec .venv/bin/python -m app.server
