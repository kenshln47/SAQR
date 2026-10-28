"""recon() must ask for GeoCLIP without asking for StreetCLIP. No uv, no weights."""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("SAQR_CASES", tempfile.mkdtemp(prefix="saqr-recon-"))

import pytest

import app.tools as T


class _Case:
    def __init__(self, folder, rev: bool):
        self.dir = folder
        self.photo = folder / "photo.jpg"
        self._rev = rev

    def load(self):
        return {"rev": self._rev}


def _fake(calls, write_md: bool):
    def run(case, script, args, **kwargs):
        calls.append((script, list(args), kwargs.get("use_uv"), kwargs.get("timeout")))
        if write_md and script == "recon.py":
            out = case.dir / "work" / "recon"
            out.mkdir(parents=True, exist_ok=True)
            (out / "recon.md").write_text("recon ok", encoding="utf-8")
        return 0, ""

    return run


def test_commercial_recon_calls_geoclip_after_skip(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("SAQR_ALLOW_NC_MODELS", raising=False)
    calls: list = []
    monkeypatch.setattr(T, "run_script", _fake(calls, True))
    out = T.recon(_Case(tmp_path, rev=False))
    assert not out.is_error
    assert calls[0][0] == "recon.py"
    skip_at = calls[0][1].index("--skip")
    assert calls[0][1][skip_at + 1] == "calib,prior"
    assert "--no-rev" in calls[0][1]
    assert calls[1][0] == "prior.py"
    assert calls[1][1][-2:] == ["--models", "geoclip"]
    assert "streetclip" not in calls[1][1]
    assert calls[1][1][calls[1][1].index("--out-dir") + 1] == "recon/prior"
    assert calls[1][2] is True and calls[1][3] == 1800


def test_nc_opt_in_does_not_add_a_prior_call(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("SAQR_ALLOW_NC_MODELS", "1")
    calls: list = []
    monkeypatch.setattr(T, "run_script", _fake(calls, True))
    T.recon(_Case(tmp_path, rev=True))
    assert len(calls) == 1
    skip_at = calls[0][1].index("--skip")
    assert calls[0][1][skip_at + 1] == "calib"
    assert "--no-rev" not in calls[0][1]
