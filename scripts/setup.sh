#!/bin/sh
# Linux and macOS setup. Windows keeps setup.bat. Same app pins.
# torch is the CPU index unless nvidia-smi can see a GPU, then the cu130 index.
set -eu
cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed. See https://docs.astral.sh/uv/" >&2
  exit 1
fi

uv venv --allow-existing --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python --no-deps streetlevel==0.12.13

TORCH_INDEX="https://download.pytorch.org/whl/cpu"
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  TORCH_INDEX="https://download.pytorch.org/whl/cu130"
fi
echo "torch index: $TORCH_INDEX"
uv pip install --python .venv/bin/python torch torchvision --index-url "$TORCH_INDEX"

if [ ! -f .env ]; then
  cp .env.example .env
fi

.venv/bin/python -m app.geoint_fetch
echo "Done. Run scripts/run.sh, then open Settings to add an OpenRouter or Anthropic key."
