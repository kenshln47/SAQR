"""L-PHOTO-01: a case with no original file raises, it does not index an empty list."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

os.environ.setdefault("SAQR_CASES", tempfile.mkdtemp(prefix="saqr-photo-"))

from app.cases import Case


def test_missing_original_raises(tmp_path) -> None:
    folder = tmp_path / "2026-01-01_saqr-x-abcdef"
    (folder / "original").mkdir(parents=True)
    (folder / "case.json").write_text(json.dumps({"id": folder.name}), encoding="utf-8")
    case = Case(folder)
    with pytest.raises(FileNotFoundError):
        _ = case.photo


def test_present_original_is_returned(tmp_path) -> None:
    folder = tmp_path / "2026-01-01_saqr-y-abcdef"
    (folder / "original").mkdir(parents=True)
    photo = folder / "original" / "photo.png"
    photo.write_bytes(b"png")
    (folder / "case.json").write_text("{}", encoding="utf-8")
    assert Case(folder).photo == photo
