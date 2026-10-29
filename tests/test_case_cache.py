"""H-LOAD-01: case.json is read once per process, then served from the cache `_save` updates."""
from __future__ import annotations

import json
import os
import tempfile

os.environ.setdefault("SAQR_CASES", tempfile.mkdtemp(prefix="saqr-cache-"))

from app.cases import Case


def _case(tmp_path) -> Case:
    folder = tmp_path / "2026-01-01_saqr-x-abcdef"
    folder.mkdir()
    (folder / "case.json").write_text(
        json.dumps({"id": folder.name, "status": "queued", "candidates": []}), encoding="utf-8")
    (folder / "events.jsonl").write_text("", encoding="utf-8")
    return Case(folder)


def test_two_loads_after_update_do_not_reread(tmp_path) -> None:
    case = _case(tmp_path)
    case.update(status="done", marker=1)
    assert case.disk_reads() == 1
    first = case.load()
    second = case.load()
    assert first["status"] == "done" and first["marker"] == 1
    assert second["marker"] == 1
    assert case.disk_reads() == 1


def test_a_second_object_sees_the_same_cache(tmp_path) -> None:
    case = _case(tmp_path)
    case.update(marker=7)
    other = Case(case.dir)
    assert other.load()["marker"] == 7
    assert other.disk_reads() == 1


def test_callers_cannot_mutate_the_cache(tmp_path) -> None:
    case = _case(tmp_path)
    case.load()["status"] = "hacked"
    assert case.load()["status"] == "queued"
    assert case.disk_reads() == 1
