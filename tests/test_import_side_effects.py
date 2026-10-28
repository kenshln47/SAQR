"""M-IMPORT-01: importing the app must not create directories or fail a live case."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _env(cases: str) -> dict[str, str]:
    env = os.environ.copy()
    env["SAQR_CASES"] = cases
    env["PYTHONPATH"] = ROOT
    return env


def test_import_does_not_create_the_cases_directory(tmp_path) -> None:
    target = tmp_path / "not-created"
    result = subprocess.run(
        [sys.executable, "-c", "import app.server"],
        cwd=ROOT, env=_env(str(target)), capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert not target.exists()


def test_import_does_not_fail_a_live_case(tmp_path) -> None:
    root = tmp_path / "cases"
    folder = root / "2026-01-01_saqr-live-abcdef"
    folder.mkdir(parents=True)
    (folder / "case.json").write_text(json.dumps({
        "id": folder.name, "status": "analysing", "created": "t", "updated": "t",
        "filename": "a.png", "candidates": [], "final": None,
    }), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-c", "import app.server"],
        cwd=ROOT, env=_env(str(root)), capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    saved = json.loads((folder / "case.json").read_text(encoding="utf-8"))
    assert saved["status"] == "analysing"


def test_a_taken_port_is_refused_before_any_server_object_is_needed() -> None:
    from app.server import bind_loopback
    held = socket.socket()
    held.bind(("127.0.0.1", 0))
    port = held.getsockname()[1]
    try:
        with pytest.raises(SystemExit):
            bind_loopback(port)
    finally:
        held.close()


def test_bind_loopback_owns_an_ephemeral_port() -> None:
    from app.server import bind_loopback
    sock = bind_loopback(0)
    try:
        assert sock.getsockname()[0] == "127.0.0.1"
        assert sock.getsockname()[1] > 0
    finally:
        sock.close()
