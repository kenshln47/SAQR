"""M-PKG-01: Linux/macOS scripts exist, and the dependency pins have one list."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _requirement_pins() -> list[str]:
    pins = []
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            pins.append(line)
    return pins


def test_requirements_are_the_pyproject_dependencies() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for pin in _requirement_pins():
        assert pin in project, pin


def test_lock_records_torch_and_streetlevel_without_pyfrpc() -> None:
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "torch"' in lock
    assert 'name = "streetlevel"' in lock
    assert 'name = "pyexiv2"' in lock
    assert "pyfrpc" not in lock
    workflow = (ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
    assert "uv pip install --python .venv/bin/python pytest ruff pillow" in workflow
    assert "https://download.pytorch.org/whl/cpu" in workflow
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "torch==" not in requirements
    assert "streetlevel==" not in requirements
    assert "pyexiv2==2.16.0" in requirements
    assert "pyfrpc" not in lock
    setup = (ROOT / "scripts" / "setup.sh").read_text(encoding="utf-8")
    assert "nvidia-smi" in setup
    assert "https://download.pytorch.org/whl/cpu" in setup
    assert "https://download.pytorch.org/whl/cu130" in setup
    bat = (ROOT / "setup.bat").read_text(encoding="utf-8")
    assert "nvidia-smi" in bat
    assert bat.index("https://download.pytorch.org/whl/cpu") < bat.index("https://download.pytorch.org/whl/cu130")
    assert "|| uv pip install --python %VP% torch torchvision\n" not in bat


def test_shell_entrypoints_exist_and_bind_locally() -> None:
    setup = (ROOT / "scripts" / "setup.sh").read_text(encoding="utf-8")
    run = (ROOT / "scripts" / "run.sh").read_text(encoding="utf-8")
    assert "requirements.txt" in setup
    assert "app.server" in run
    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    command = docker.split("CMD", 1)[1]
    assert "0.0.0.0" not in command
    assert "app.server" in command
    assert (ROOT / "uv.lock").is_file()
