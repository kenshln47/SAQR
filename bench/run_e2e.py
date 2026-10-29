#!/usr/bin/env python3
"""Run the geolocation agent on the corpus. Does not invent a score.

Two tiers, street mode, SAQR_EFFORT=medium, four configurations:
  flash     every manifest photo on z-ai/glm-5.3-flash. Writes flash.json.
            That file is a harness check. It is not the product number.
  headline  a 50-photo stratified subset on anthropic/claude-opus-5.5.
            Writes score.json only when every selected photo has a row in
            every configuration.

Without a provider key the process exits 2 and does not write score.json.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench.e2e import CONFIGS, FLASH_MODEL, HEADLINE_MODEL, aggregate, headline_rows, output_paths, strip_exif  # noqa: E402

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


def _prepare_model(tier: str) -> str:
    if tier == "flash":
        os.environ["SAQR_PROVIDER"] = "openrouter"
        os.environ["SAQR_OR_MODEL"] = FLASH_MODEL
        return FLASH_MODEL
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        os.environ["SAQR_PROVIDER"] = "anthropic"
        os.environ["SAQR_MODEL"] = "claude-opus-5-5"
        return HEADLINE_MODEL
    os.environ["SAQR_PROVIDER"] = "openrouter"
    os.environ["SAQR_OR_MODEL"] = HEADLINE_MODEL
    return HEADLINE_MODEL


def _tier_ready(tier: str) -> bool:
    if tier == "flash":
        return bool(os.environ.get("OPENROUTER_API_KEY"))
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("OPENROUTER_API_KEY"))


def main(argv: list[str] | None = None) -> int:
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
    args = list(sys.argv[1:] if argv is None else argv)
    tier = args[0] if args else os.environ.get("SAQR_E2E_TIER", "")
    if tier not in ("flash", "headline"):
        print("tier must be flash or headline. score.json was not written.", file=sys.stderr)
        return 2
    if not _tier_ready(tier):
        print(f"{tier} has no key for its provider. score.json was not written.", file=sys.stderr)
        return 2
    model = _prepare_model(tier)
    manifest = _manifest()
    selected = manifest if tier == "flash" else headline_rows(manifest)
    detail_name, done_name = output_paths(tier)
    detail_path = CORPUS / detail_name
    done = _done(detail_path)
    with detail_path.open("a", encoding="utf-8") as fh:
        for cfg in CONFIGS:
            for row in selected:
                key = (cfg["id"], row["id"])
                if key in done:
                    continue
                photo = CORPUS / row["file"]
                try:
                    packed = _one(photo, row, cfg)
                except Exception as exc:
                    packed = {
                        "id": row["id"], "config": cfg["id"], "stratum": row.get("stratum"),
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                packed["model"] = model
                packed["tier"] = tier
                fh.write(json.dumps(packed, ensure_ascii=False) + "\n")
                fh.flush()
                done.add(key)
    detail = [json.loads(line) for line in detail_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    need = len(selected) * len(CONFIGS)
    if len(detail) < need:
        print(f"incomplete {len(detail)}/{need}. {done_name} was not written.", file=sys.stderr)
        return 2
    result = aggregate(detail)
    result["tier"] = tier
    result["model"] = model
    result["n_manifest"] = len(selected)
    result["n_corpus"] = len(manifest)
    result["by_stratum_manifest"] = {}
    for row in selected:
        result["by_stratum_manifest"][row.get("stratum") or ""] = result["by_stratum_manifest"].get(row.get("stratum") or "", 0) + 1
    if tier == "flash":
        result["what"] = (
            "Harness check on z-ai/glm-5.3-flash. Not the product number. "
            "score.json is the headline tier on anthropic/claude-opus-5.5."
        )
    else:
        result["what"] = (
            "Headline end-to-end agent loop on anthropic/claude-opus-5.5, stratified subset. "
            "Not a GeoCLIP-only prior score. Not the flash model. "
            "OR_DEFAULT is not re-ranked from a partial file."
        )
    out = CORPUS / done_name
    out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({"tier": tier, "model": model, "n": len(selected), "file": done_name}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
