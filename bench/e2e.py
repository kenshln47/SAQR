"""End-to-end score shape. The runner is bench/run_e2e.py.

Four configurations, one photo each, medium effort, the agent loop:
  prior_rev, prior_norev          StreetCLIP+GeoCLIP inside recon (NC opt-in)
  skip_prior_rev, skip_prior_norev  commercial path: --skip calib,prior then GeoCLIP only

Reverse search is the other factor. A GeoCLIP-only file is not this score.
OR_DEFAULT is not ranked from an eye benchmark. This module does not call a model.
"""
from __future__ import annotations

import io

from PIL import Image

from app.benchscore import score as score_rows

CONFIGS = (
    {"id": "prior_rev", "nc_models": True, "rev": True},
    {"id": "prior_norev", "nc_models": True, "rev": False},
    {"id": "skip_prior_rev", "nc_models": False, "rev": True},
    {"id": "skip_prior_norev", "nc_models": False, "rev": False},
)

# 14+9+9+8+6+4 = 50. Stable: lowest ids in each stratum. Not a flash-model score.
HEADLINE_TAKE = (
    ("city", 14),
    ("town", 9),
    ("rural", 9),
    ("gulf", 8),
    ("interior", 6),
    ("screenshot", 4),
)
FLASH_MODEL = "z-ai/glm-5.3-flash"
HEADLINE_MODEL = "anthropic/claude-opus-5.5"


def headline_rows(manifest: list[dict]) -> list[dict]:
    """Stratified 50 for the opus headline. Short strata contribute what they have. No invented rows."""
    grouped: dict[str, list[dict]] = {}
    for row in manifest:
        grouped.setdefault(row.get("stratum") or "", []).append(row)
    for rows in grouped.values():
        rows.sort(key=lambda r: str(r.get("id") or ""))
    chosen: list[dict] = []
    for stratum, n in HEADLINE_TAKE:
        chosen.extend(grouped.get(stratum, [])[:n])
    return chosen


def output_paths(tier: str) -> tuple[str, str]:
    """Detail file, finished file. Flash never writes score.json."""
    if tier == "flash":
        return "flash_detail.jsonl", "flash.json"
    if tier == "headline":
        return "headline_detail.jsonl", "score.json"
    raise ValueError(tier)


def strip_exif(data: bytes) -> bytes:
    """Drop EXIF, including a GPS tag, so recon cannot read the truth off the file."""
    im = Image.open(io.BytesIO(data))
    im = im.convert("RGB")
    out = io.BytesIO()
    im.save(out, "JPEG", quality=90)
    return out.getvalue()


def _group(rows: list[dict]) -> dict:
    return {
        "all": score_rows(rows),
        "by_stratum": {
            stratum: score_rows([r for r in rows if r.get("stratum") == stratum])
            for stratum in sorted({r.get("stratum") or "" for r in rows})
        },
    }


def aggregate(detail: list[dict]) -> dict:
    """Per configuration, then per stratum. Rows without a filed lat/lon are counted as missing."""
    out = {}
    for cfg in CONFIGS:
        rows = [r for r in detail if r.get("config") == cfg["id"] and r.get("pred_lat") is not None]
        block = _group(rows)
        block["n_detail"] = sum(1 for r in detail if r.get("config") == cfg["id"])
        block["n_scored"] = len(rows)
        out[cfg["id"]] = block
    return {
        "what": (
            "End-to-end agent loop. Not a GeoCLIP-only prior score. "
            "Not an eye benchmark. OR_DEFAULT is not re-ranked from this file unless every config finished."
        ),
        "effort": "medium",
        "configs": out,
    }
