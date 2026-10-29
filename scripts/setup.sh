#!/bin/sh
# Linux and macOS setup. Windows keeps setup.bat. Same app pins.
# torch/torchvision are the PyPI default wheels. That is the CUDA build, not a CPU index.
# This script does not select a GPU. A machine without one still downloads the CUDA wheels.
set -eu
cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed. See https://docs.astral.sh/uv/" >&2
  exit 1
fi

uv venv --allow-existing --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python --no-deps streetlevel==0.12.13
uv pip install --python .venv/bin/python torch torchvision

if [ ! -f .env ]; then
  cp .env.example .env
fi

.venv/bin/python -m app.geoint_fetch
echo "Done. Run scripts/run.sh, then open Settings to add an OpenRouter or Anthropic key."
