"""M-GEOINT-01: setup clones GeoInt when scripts/recon.py is missing, and leaves a present install alone."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.geoint_fetch import GEOINT_URL, ensure_geoint

ROOT = Path(__file__).resolve().parents[1]


def test_an_existing_skill_is_not_cloned(tmp_path) -> None:
    marker = tmp_path / "scripts" / "recon.py"
    marker.parent.mkdir()
    marker.write_text("# recon\n", encoding="utf-8")
    calls = []
    assert ensure_geoint(tmp_path, runner=lambda *a, **k: calls.append(a)) == "present"
    assert calls == []


def test_clone_writes_the_marker(tmp_path) -> None:
    dest = tmp_path / "geoint"

    def runner(cmd, **_kwargs):
        assert cmd[:4] == ["git", "clone", "--depth", "1"]
        assert GEOINT_URL in cmd
        folder = Path(cmd[-1])
        (folder / "scripts").mkdir(parents=True)
        (folder / "scripts" / "recon.py").write_text("# recon\n", encoding="utf-8")

        class Result:
            returncode = 0
            stderr = ""
            stdout = ""

        return Result()

    assert ensure_geoint(dest, runner=runner) == "cloned"
    assert (dest / "scripts" / "recon.py").is_file()


def test_a_failed_clone_does_not_pretend_success(tmp_path) -> None:
    def runner(_cmd, **_kwargs):
        class Result:
            returncode = 1
            stderr = "network down"
            stdout = ""

        return Result()

    with pytest.raises(SystemExit):
        ensure_geoint(tmp_path / "missing", runner=runner)


def test_setup_scripts_call_the_fetcher() -> None:
    assert "app.geoint_fetch" in (ROOT / "scripts" / "setup.sh").read_text(encoding="utf-8")
    assert "app.geoint_fetch" in (ROOT / "setup.bat").read_text(encoding="utf-8")
    assert "app.geoint_fetch" in (ROOT / "Dockerfile").read_text(encoding="utf-8")
