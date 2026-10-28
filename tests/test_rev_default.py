"""Reverse search is off unless the case or the form says otherwise. M-REV-01."""
from __future__ import annotations

import inspect
import os
import tempfile

os.environ.setdefault("SAQR_CASES", tempfile.mkdtemp(prefix="saqr-rev-"))

import pytest

import app.tools as T
from app.server import new_case


class _Case:
    def __init__(self, folder, payload):
        self.dir = folder
        self.photo = folder / "photo.jpg"
        self._payload = payload

    def load(self):
        return self._payload


def _fake(calls):
    def run(case, script, args, **kwargs):
        calls.append(list(args))
        if script == "recon.py":
            out = case.dir / "work" / "recon"
            out.mkdir(parents=True, exist_ok=True)
            (out / "recon.md").write_text("recon ok", encoding="utf-8")
        return 0, ""

    return run


def test_upload_form_defaults_rev_off() -> None:
    default = inspect.signature(new_case).parameters["rev"].default
    assert default.default is False


def test_missing_rev_passes_no_rev(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("SAQR_ALLOW_NC_MODELS", raising=False)
    calls: list = []
    monkeypatch.setattr(T, "run_script", _fake(calls))
    T.recon(_Case(tmp_path, {}))
    assert "--no-rev" in calls[0]


def test_stored_rev_still_searches(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("SAQR_ALLOW_NC_MODELS", raising=False)
    calls: list = []
    monkeypatch.setattr(T, "run_script", _fake(calls))
    T.recon(_Case(tmp_path, {"rev": True}))
    assert "--no-rev" not in calls[0]
