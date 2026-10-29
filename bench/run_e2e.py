#!/usr/bin/env python3
"""Run the geolocation agent on the corpus. Does not invent a score.

One street-mode run per photo per configuration, SAQR_EFFORT=medium.
Writes e2e_detail.jsonl as it goes and score.json only when every photo
has a row in every configuration. Without a provider key it exits 2 and
does not write score.json.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench.e2e import CONFIGS, aggregate, strip_exif  # noqa: E402

CORPUS = Path(os.environ.get("SAQR_CORPUS", "/var/saqr-corpus")).resolve()


def has_ai() -> bool:
    from app.config import has_ai as _has_ai
    return _has_ai()


def _manifest() -> list[dict]:
    path = CORPUS / "manifest.jsonl"
    if not path.is_file():
        sys.exit(f"missing {path}")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _done(path: Path) -> set[tuple[str, str]]:
    if not path.is_file():
        return set()
    out = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        out.add((row.get("config", ""), row.get("id", "")))
    return out


def _apply_config(cfg: dict) -> None:
    if cfg["nc_models"]:
        os.environ["SAQR_ALLOW_NC_MODELS"] = "1"
    else:
        os.environ.pop("SAQR_ALLOW_NC_MODELS", None)


def _one(photo: Path, manifest: dict, cfg: dict) -> dict:
    from app.agent import run_geolocate
    from app.cases import create

    _apply_config(cfg)
    data = strip_exif(photo.read_bytes())
    case = create(photo.name, data, "street", rev=cfg["rev"])
    run_geolocate(case, "street")
    final = case.load().get("final") or {}
    lat, lon = final.get("lat"), final.get("lon")
    row = {
        "id": manifest["id"],
        "config": cfg["id"],
        "stratum": manifest.get("stratum"),
        "scene": manifest.get("scene"),
        "true_lat": manifest.get("lat"),
        "true_lon": manifest.get("lon"),
        "country_true": manifest.get("country") or None,
        "country_pred": final.get("country"),
        "radius_km": final.get("radius_km"),
        "confidence": final.get("confidence"),
        "level": final.get("level"),
        "case": case.id,
        "nc_models": cfg["nc_models"],
        "rev": cfg["rev"],
    }
    if lat is None or lon is None:
        row["error"] = case.load().get("error") or "no final lat/lon"
        return row
    row["pred_lat"] = lat
    row["pred_lon"] = lon
    return row


def main() -> int:
    os.environ["SAQR_EFFORT"] = "medium"
    os.environ.setdefault("SAQR_CASES", "/var/saqr-corpus/e2e-cases")
    if not has_ai():
        print(
            "no provider key. ANTHROPIC_API_KEY and OPENROUTER_API_KEY are empty. "
            "The agent loop did not run. score.json was not written. "
            "A GeoCLIP-only file is not this score.",
            file=sys.stderr,
        )
        return 2
    manifest = _manifest()
    detail_path = CORPUS / "e2e_detail.jsonl"
    done = _done(detail_path)
    with detail_path.open("a", encoding="utf-8") as fh:
        for cfg in CONFIGS:
            for row in manifest:
                key = (cfg["id"], row["id"])
                if key in done:
                    continue
                photo = CORPUS / row["file"]
                try:
                    packed = _one(photo, row, cfg)
                except (OSError, ValueError) as exc:
                    packed = {"id": row["id"], "config": cfg["id"], "stratum": row.get("stratum"), "error": str(exc)}
                fh.write(json.dumps(packed, ensure_ascii=False) + "\n")
                fh.flush()
                done.add(key)
    detail = [json.loads(line) for line in detail_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    need = len(manifest) * len(CONFIGS)
    if len(detail) < need:
        print(f"incomplete {len(detail)}/{need}. score.json was not written.", file=sys.stderr)
        return 2
    result = aggregate(detail)
    result["n_manifest"] = len(manifest)
    result["by_stratum_manifest"] = {}
    for row in manifest:
        result["by_stratum_manifest"][row.get("stratum") or ""] = result["by_stratum_manifest"].get(row.get("stratum") or "", 0) + 1
    out = CORPUS / "score.json"
    out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({"n_manifest": len(manifest), "configs": list(result["configs"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
