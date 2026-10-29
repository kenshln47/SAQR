"""H-ID-01: case ids cannot be . or .. and cannot resolve outside CASES_DIR."""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("SAQR_CASES", tempfile.mkdtemp(prefix="saqr-id-"))

from app import cases


def test_dotdot_does_not_open_the_parent(tmp_path, monkeypatch) -> None:
    root = tmp_path / "cases"
    root.mkdir()
    (tmp_path / "case.json").write_text('{"id": "parent"}', encoding="utf-8")
    monkeypatch.setattr(cases, "CASES_DIR", root)
    assert cases.get("..") is None
    assert cases.get(".") is None
    assert cases.get("../case") is None


def test_symlink_cannot_leave_the_cases_dir(tmp_path, monkeypatch) -> None:
    root = tmp_path / "cases"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "case.json").write_text("{}", encoding="utf-8")
    (root / "linked").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(cases, "CASES_DIR", root)
    assert cases.get("linked") is None


def test_a_real_case_id_still_opens(tmp_path, monkeypatch) -> None:
    root = tmp_path / "cases"
    cid = "2026-01-01_saqr-photo-abc123"
    folder = root / cid
    folder.mkdir(parents=True)
    (folder / "case.json").write_text('{"id": "%s", "status": "done"}' % cid, encoding="utf-8")
    monkeypatch.setattr(cases, "CASES_DIR", root)
    found = cases.get(cid)
    assert found is not None
    assert found.id == cid
