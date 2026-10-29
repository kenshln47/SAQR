#!/usr/bin/env python3
"""Score the local prior on SAQR_CORPUS. Does not score the tool-using agent.

Writes score.json next to the manifest. The photos stay in that directory.
No API key is read. OR_DEFAULT is not changed.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GEOINT = Path(os.environ.get("SAQR_GEOINT", Path.home() / ".claude/skills/geoint"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(GEOINT / "scripts"))

import prior  # noqa: E402
from app.benchscore import score as score_rows  # noqa: E402

CORPUS = Path(os.environ.get("SAQR_CORPUS", "/var/saqr-corpus")).resolve()


def _rows() -> list[dict]:
    path = CORPUS / "manifest.jsonl"
    if not path.is_file():
        sys.exit(f"missing {path}")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _geoclip_one(model, im: Image.Image) -> dict:
    ims = prior.crops(im)
    pts, probs = model.points(ims, 100)
    total = float(probs.sum()) or 1.0
    clusters = prior.cluster(pts, probs, 150.0)
    clusters = [{**c, "mass": c["mass"] / total} for c in clusters[:10]]
    mass: dict[str, float] = {}
    for cluster in clusters:
        cc = ((cluster.get("near") or {}).get("country")) or ""
        if cc:
            mass[cc] = mass.get(cc, 0.0) + float(cluster["mass"])
    countries = [{"iso2": k, "p": v} for k, v in sorted(mass.items(), key=lambda kv: -kv[1])]
    guess = prior.best_guess({"combined": countries, "geoclip": {"clusters": clusters, "points": [
        [float(a), float(b), float(c)] for (a, b), c in list(zip(pts.tolist(), probs.tolist()))[:50]
    ]}})
    top = clusters[0] if clusters else None
    return {
        "countries": countries[:5],
        "top_cluster": None if not top else {"lat": top["lat"], "lon": top["lon"]},
        "best_guess": None if not guess else {"lat": guess["lat"], "lon": guess["lon"], "country": guess["country"], "how": guess["how"]},
        "confidence": countries[0]["p"] if countries else None,
        "clusters": clusters,
        "points": [[round(float(a), 4), round(float(b), 4), round(float(c), 6)] for (a, b), c in list(zip(pts.tolist(), probs.tolist()))[:50]],
    }


def _pack(manifest: dict, pred: dict | None, how: str) -> dict | None:
    if not pred or pred.get("lat") is None:
        return None
    return {
        "id": manifest["id"],
        "stratum": manifest["stratum"],
        "scene": manifest["scene"],
        "true_lat": manifest["lat"],
        "true_lon": manifest["lon"],
        "pred_lat": pred["lat"],
        "pred_lon": pred["lon"],
        "country_true": manifest.get("country") or None,
        "country_pred": pred.get("country"),
        "confidence": pred.get("confidence"),
        "how": how,
    }


def _by_stratum(rows: list[dict]) -> dict:
    out = {}
    for stratum in sorted({r["stratum"] for r in rows}):
        out[stratum] = score_rows([r for r in rows if r["stratum"] == stratum])
    return out


def main() -> int:
    manifest = _rows()
    t0 = time.time()
    model = prior.GeoCLIPModel("cpu")
    raw_cluster = []
    raw_guess = []
    detail_path = CORPUS / "geoclip_detail.jsonl"
    detail_fh = detail_path.open("w", encoding="utf-8")
    for i, row in enumerate(manifest, 1):
        path = CORPUS / row["file"]
        try:
            im = Image.open(path)
            one = _geoclip_one(model, im)
        except (OSError, ValueError) as exc:
            detail_fh.write(json.dumps({"id": row["id"], "error": str(exc)}) + "\n")
            continue
        cluster = one["top_cluster"]
        guess = one["best_guess"] or {}
        packed_c = _pack(row, {**(cluster or {}), "country": (one["countries"][0]["iso2"] if one["countries"] else None), "confidence": one["confidence"]}, "geoclip-top-cluster")
        packed_g = _pack(row, {**guess, "confidence": one["confidence"]}, "geoclip-best-guess")
        if packed_c:
            raw_cluster.append(packed_c)
        if packed_g:
            raw_guess.append(packed_g)
        detail_fh.write(json.dumps({"id": row["id"], "stratum": row["stratum"], "scene": row["scene"], "geoclip": one}, ensure_ascii=False) + "\n")
        detail_fh.flush()
        if i % 10 == 0:
            print(f"geoclip {i}/{len(manifest)} {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
    detail_fh.close()
    del model
    result = {
        "what": "local prior only. Not the SAQR agent, not a vision-LLM ranking, not a claim that the product is accurate.",
        "corpus": str(CORPUS),
        "n_manifest": len(manifest),
        "device": "cpu",
        "seconds": round(time.time() - t0, 1),
        "geoclip_top_cluster": score_rows(raw_cluster),
        "geoclip_best_guess": score_rows(raw_guess),
        "geoclip_best_guess_by_stratum": _by_stratum(raw_guess),
        "rows_best_guess": raw_guess,
    }
    out = CORPUS / "score.json"
    out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("n_manifest", "seconds", "geoclip_top_cluster", "geoclip_best_guess")}))
    return 0 if raw_guess else 2


if __name__ == "__main__":
    sys.exit(main())
