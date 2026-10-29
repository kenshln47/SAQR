"""Paths and settings for SAQR. Everything runs locally; only the AI reasoning step calls out."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # the saqr folder


def load_dotenv() -> None:
    """Read saqr/.env (KEY=VALUE lines) into the environment without overriding what is already set."""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_dotenv()   # before the settings below, so .env can set them

# one folder per case; SAQR_CASES moves them
def _cases_dir() -> Path:
    """SAQR_CASES if set; else the folder above saqr when it already holds SAQR cases (older installs keep their
    cases where they are); else saqr\\cases, so a fresh clone never writes photos into Documents or Desktop."""
    if os.environ.get("SAQR_CASES"):
        return Path(os.environ["SAQR_CASES"]).expanduser().resolve()
    legacy = ROOT.parent
    if (legacy / "saqr_board.json").exists() or next(legacy.glob("*_saqr-*/case.json"), None):
        return legacy.resolve()
    return (ROOT / "cases").resolve()


CASES_DIR = _cases_dir()


def ensure_cases_dir() -> Path:
    """Create the cases directory when a server is actually starting, not at import."""
    CASES_DIR.mkdir(parents=True, exist_ok=True)
    return CASES_DIR


WEB_DIR = ROOT / "web"
GEOINT = Path(os.environ.get("SAQR_GEOINT") or Path.home() / ".claude" / "skills" / "geoint")
SCRIPTS = GEOINT / "scripts"
VENV_PY = Path(sys.executable)                          # this venv has streetlevel without pyfrpc
UV = os.environ.get("UV", "uv")

MODEL = os.environ.get("SAQR_MODEL", "claude-opus-5-5")
EFFORT = os.environ.get("SAQR_EFFORT", "high")
MAX_TURNS = int(os.environ.get("SAQR_MAX_TURNS") or 40)
SECRET_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENROUTER_API_KEY")   # never handed to subprocesses


OR_DEFAULT = "anthropic/claude-opus-5.5"


def provider() -> str:
    """Which service runs the reasoning step: 'anthropic', 'openrouter', or '' (local models only).
    SAQR_PROVIDER picks one when both keys are saved."""
    has_an = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    has_or = bool(os.environ.get("OPENROUTER_API_KEY"))
    want = os.environ.get("SAQR_PROVIDER", "")
    if want == "openrouter" and has_or:
        return "openrouter"
    if want == "anthropic" and has_an:
        return "anthropic"
    return "anthropic" if has_an else "openrouter" if has_or else ""


def has_ai() -> bool:
    return bool(provider())


def model_name() -> str:
    if provider() == "openrouter":
        return os.environ.get("SAQR_OR_MODEL") or OR_DEFAULT
    return os.environ.get("SAQR_MODEL") or MODEL


def engine_label() -> str:
    return f"{'OpenRouter' if provider() == 'openrouter' else 'Claude'} ({model_name()})"
