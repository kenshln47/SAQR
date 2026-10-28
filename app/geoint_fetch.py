"""Clone the GeoInt skill when this machine does not already have it.

The scripts are MIT and stay outside this repository. A present install is left alone.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

GEOINT_URL = "https://github.com/marouane53/GeoInt.git"


def geoint_dest() -> Path:
    raw = os.environ.get("SAQR_GEOINT", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".claude" / "skills" / "geoint"


def ensure_geoint(dest: Path | None = None, runner=None) -> str:
    """Return 'present' or 'cloned'. Exit if the clone does not produce scripts/recon.py."""
    folder = dest or geoint_dest()
    marker = folder / "scripts" / "recon.py"
    if marker.is_file():
        return "present"
    if folder.exists() and any(folder.iterdir()):
        raise SystemExit(f"{folder} exists but has no scripts/recon.py. Not overwriting it.")
    if folder.exists():
        folder.rmdir()
    folder.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "--depth", "1", GEOINT_URL, str(folder)]
    run = runner or subprocess.run
    result = run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not marker.is_file():
        detail = (result.stderr or result.stdout or "").strip()
        raise SystemExit(f"could not clone GeoInt into {folder}: {detail[:400]}")
    return "cloned"


def main() -> None:
    print(ensure_geoint())


if __name__ == "__main__":
    main()
