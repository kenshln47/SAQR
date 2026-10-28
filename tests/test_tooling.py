"""M-TEST-01: pytest, ruff, and the GitHub workflow stay in the tree."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pytest_and_ruff_are_configured() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.pytest.ini_options]" in text
    assert 'testpaths = ["tests"]' in text
    assert "[tool.ruff" in text
    assert "E9" in text


def test_the_workflow_runs_ruff_and_pytest() -> None:
    text = (ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
    assert "ruff check app tests" in text
    assert "pytest -q" in text
    assert "torch" not in text


def test_there_is_more_than_one_test_module() -> None:
    modules = list((ROOT / "tests").glob("test_*.py"))
    assert len(modules) >= 5
