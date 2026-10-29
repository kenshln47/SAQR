"""H-POOL-01: the (N+1)th submission waits, and the case meter adds up."""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time

os.environ.setdefault("SAQR_CASES", tempfile.mkdtemp(prefix="saqr-pool-"))

from app.cases import Case
from app.pool import WorkerPool, worker_count


def test_the_extra_submission_waits() -> None:
    pool = WorkerPool(1)
    started = threading.Event()
    release = threading.Event()

    def first() -> None:
        started.set()
        assert release.wait(3)

    pool.submit(first)
    assert started.wait(1)
    finished = threading.Event()
    thread = threading.Thread(target=lambda: pool.submit(lambda: finished.set()))
    thread.start()
    for _ in range(50):
        if pool.waiters == 1:
            break
        time.sleep(0.02)
    assert pool.waiters == 1
    assert not finished.is_set()
    release.set()
    thread.join(3)
    assert finished.wait(1)


def test_worker_count_defaults_and_caps(monkeypatch) -> None:
    monkeypatch.delenv("SAQR_WORKERS", raising=False)
    assert worker_count() == 2
    monkeypatch.setenv("SAQR_WORKERS", "99")
    assert worker_count() == 8
    monkeypatch.setenv("SAQR_WORKERS", "0")
    assert worker_count() == 1
    monkeypatch.setenv("SAQR_WORKERS", "nope")
    assert worker_count() == 2


def test_cost_meter_adds(tmp_path) -> None:
    folder = tmp_path / "2026-01-01_saqr-cost-abcdef"
    folder.mkdir()
    (folder / "case.json").write_text(json.dumps({"id": folder.name, "status": "analysing"}), encoding="utf-8")
    (folder / "events.jsonl").write_text("", encoding="utf-8")
    case = Case(folder)
    case.add_cost(turns=1, tools=2)
    case.add_cost(turns=1, tools=1)
    assert case.load()["cost"] == {"turns": 2, "tools": 3}
    assert [ev["kind"] for ev in case.events()].count("cost") == 2
