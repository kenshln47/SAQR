"""H-SSE-01: the stream tails an in-memory index. The hot path does not re-read events.jsonl."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("SAQR_CASES", tempfile.mkdtemp(prefix="saqr-events-"))

from app.cases import Case


def _case(tmp_path) -> Case:
    folder = tmp_path / "2026-01-01_saqr-ev-abcdef"
    folder.mkdir()
    (folder / "case.json").write_text(json.dumps({"id": folder.name, "status": "done"}), encoding="utf-8")
    (folder / "events.jsonl").write_text("", encoding="utf-8")
    return Case(folder)


def test_tail_from_the_last_index_does_not_reread(tmp_path, monkeypatch) -> None:
    case = _case(tmp_path)
    for i in range(5):
        case.emit("log", text=str(i))
    reads = {"n": 0}
    original = Path.read_text

    def counting(self, *args, **kwargs):
        if self.name == "events.jsonl":
            reads["n"] += 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counting)
    tail = case.events(4)
    assert [ev["text"] for ev in tail] == ["4"]
    assert reads["n"] == 0
    assert case.event_reads() == 1


def test_a_corrupt_line_is_kept_as_a_log(tmp_path) -> None:
    case = _case(tmp_path)
    (case.dir / "events.jsonl").write_text('{"kind":"log","text":"ok"}\nNOT JSON\n', encoding="utf-8")
    evs = case.events()
    assert evs[0]["text"] == "ok"
    assert evs[1]["kind"] == "log"
    assert "تالف" in evs[1]["text"]
