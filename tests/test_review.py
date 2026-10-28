"""Case.review writes truth on confirm and leaves it alone on dismiss."""
from __future__ import annotations

import json
import os
import tempfile

os.environ.setdefault("SAQR_CASES", tempfile.mkdtemp(prefix="saqr-review-"))

import pytest

from app.cases import Case


def _case(tmp_path, *, candidates=None, final=None) -> Case:
    folder = tmp_path / "2026-10-28_saqr-photo-abc123"
    (folder / "original").mkdir(parents=True)
    (folder / "original" / "photo.png").write_bytes(b"\x89PNG\r\n")
    (folder / "events.jsonl").write_text("", encoding="utf-8")
    (folder / "case.json").write_text(json.dumps({
        "id": folder.name, "mode": "region", "status": "done",
        "candidates": candidates or [], "final": final,
    }), encoding="utf-8")
    return Case(folder)


def test_confirm_candidate_writes_truth_and_error(tmp_path) -> None:
    case = _case(
        tmp_path,
        candidates=[{"n": 1, "lat": 24.8, "lon": 46.8, "label": "x"}],
        final={"lat": 24.7, "lon": 46.7, "country": "Saudi Arabia"},
    )
    saved = case.review("confirmed", n=1)
    truth = saved["truth"]
    assert truth["source"] == "analyst"
    assert truth["verdict"] == "confirmed"
    assert truth["candidate_n"] == 1
    assert truth["lat"] == 24.8 and truth["lon"] == 46.8
    assert truth["error_km"] > 0
    assert saved["candidates"][0]["review"]["verdict"] == "confirmed"
    on_disk = json.loads((case.dir / "truth.json").read_text(encoding="utf-8"))
    assert on_disk["error_km"] == truth["error_km"]
    assert any(ev.get("kind") == "review" for ev in case.events())


def test_dismiss_does_not_replace_truth(tmp_path) -> None:
    case = _case(tmp_path, final={"lat": 24.7, "lon": 46.7, "country": "Saudi Arabia"})
    case.review("confirmed")
    first = case.load()["truth"]["at"]
    saved = case.review("dismissed")
    assert saved["truth"]["at"] == first
    assert saved["final"]["review"]["verdict"] == "dismissed"
    assert json.loads((case.dir / "truth.json").read_text(encoding="utf-8"))["verdict"] == "confirmed"


def test_confirm_without_a_pin_fails(tmp_path) -> None:
    case = _case(tmp_path, final=None)
    with pytest.raises(KeyError):
        case.review("confirmed")
    assert not (case.dir / "truth.json").exists()


def test_bad_verdict_fails(tmp_path) -> None:
    case = _case(tmp_path, final={"lat": 1, "lon": 2})
    with pytest.raises(ValueError):
        case.review("maybe")
