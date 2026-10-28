"""M-LOCK-01: cases do not share one lock, and the model catalog does not hold its lock across HTTP."""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time

os.environ.setdefault("SAQR_CASES", tempfile.mkdtemp(prefix="saqr-lock-"))

from app import cases
from app import openrouter as OR
from app.cases import Case


def _case(folder) -> Case:
    folder.mkdir(parents=True)
    (folder / "case.json").write_text(json.dumps({"id": folder.name, "status": "queued"}), encoding="utf-8")
    (folder / "events.jsonl").write_text("", encoding="utf-8")
    return Case(folder)


def test_another_case_is_not_blocked(tmp_path) -> None:
    first = _case(tmp_path / "2026-01-01_saqr-a-aaaaaa")
    second = _case(tmp_path / "2026-01-01_saqr-b-bbbbbb")
    started = threading.Event()
    release = threading.Event()

    def hold() -> None:
        with first._lock():
            started.set()
            assert release.wait(2)

    thread = threading.Thread(target=hold)
    thread.start()
    assert started.wait(1)
    t0 = time.perf_counter()
    second.update(status="done")
    elapsed = time.perf_counter() - t0
    release.set()
    thread.join(2)
    assert elapsed < 0.4
    assert second.load()["status"] == "done"


def test_same_folder_shares_one_lock(tmp_path) -> None:
    folder = tmp_path / "2026-01-01_saqr-c-cccccc"
    assert cases._lock_for(folder) is cases._lock_for(folder)
    assert cases._lock_for(folder) is not cases._lock_for(tmp_path / "other")


def test_catalog_does_not_hold_the_lock_during_the_request(monkeypatch) -> None:
    OR._cat["at"] = 0.0
    OR._cat["models"] = {}
    seen: dict[str, bool] = {}

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"data": [{"id": "anthropic/claude-opus-5.5"}]}

    def fake_get(*_args, **_kwargs):
        seen["locked"] = OR._lock.locked()
        return _Response()

    monkeypatch.setattr(OR.requests, "get", fake_get)
    models = OR.catalog()
    assert seen["locked"] is False
    assert "anthropic/claude-opus-5.5" in models
