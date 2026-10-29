#!/usr/bin/env python3
"""Build a geotagged corpus outside the git tree.

Truth is a coordinate the source returned. This script does not invent one,
and it does not call Google Street View. Photos and manifest.jsonl go to
SAQR_CORPUS (default /var/saqr-corpus), never into the repo.

Panoramax frames are street-level GPS. A 2:1 equirectangular frame is stored
as a 90-degree crop of that same frame; the GPS point is unchanged.
iNaturalist rows are organism photos. Obscured locations are dropped.
Commons is used only for interior and screenshot, and only when the file
itself has coordinates. A busy Commons search is skipped, not filled in.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bench.crop import perspective_crop  # noqa: E402

CORPUS = Path(os.environ.get("SAQR_CORPUS", "/var/saqr-corpus")).resolve()
UA = {"User-Agent": "SAQR-bench/1.0 (local accuracy corpus; educational; kenshln47)"}
WANT = {"city": 50, "town": 40, "rural": 40, "gulf": 40, "interior": 20, "screenshot": 20}
MIN_TOTAL = 200

# min lon, min lat, max lon, max lat. Each box sits inside one country.
PANO_SEEDS = [
    ("city", "FR", (2.29, 48.84, 2.40, 48.90)),
    ("city", "FR", (4.80, 45.74, 4.90, 45.78)),
    ("city", "FR", (3.04, 50.62, 3.10, 50.65)),
    ("city", "FR", (-0.60, 44.82, -0.54, 44.86)),
    ("city", "FR", (7.73, 48.57, 7.78, 48.60)),
    ("city", "FR", (-1.58, 47.20, -1.52, 47.24)),
    ("city", "BE", (4.33, 50.82, 4.40, 50.87)),
    ("city", "DE", (13.36, 52.49, 13.45, 52.54)),
    ("town", "FR", (1.48, 48.44, 1.52, 48.46)),
    ("town", "FR", (1.32, 47.57, 1.36, 47.60)),
    ("town", "FR", (0.98, 47.40, 1.02, 47.43)),
    ("town", "FR", (1.60, 47.80, 1.70, 47.86)),
    ("town", "FR", (2.38, 47.07, 2.42, 47.10)),
    ("town", "FR", (4.03, 49.25, 4.08, 49.27)),
    ("town", "BE", (5.56, 50.63, 5.60, 50.65)),
    ("rural", "FR", (2.00, 48.20, 2.25, 48.40)),
    ("rural", "FR", (0.10, 48.30, 0.40, 48.55)),
    ("rural", "FR", (4.40, 46.40, 4.80, 46.70)),
    ("rural", "FR", (-1.10, 46.40, -0.60, 46.80)),
    ("rural", "FR", (5.80, 44.20, 6.20, 44.50)),
    ("gulf", "SA", (46.60, 24.60, 46.80, 24.80)),
    ("gulf", "AE", (55.20, 25.15, 55.40, 25.30)),
    ("gulf", "QA", (51.50, 25.25, 51.58, 25.35)),
]
INAT_GULF = [
    ("SA", 24.7136, 46.6753),
    ("SA", 21.4858, 39.1925),
    ("SA", 26.4207, 50.0888),
    ("SA", 21.3891, 39.8579),
    ("AE", 25.2048, 55.2708),
    ("AE", 24.4539, 54.3773),
    ("QA", 25.2854, 51.5310),
    ("KW", 29.3759, 47.9774),
    ("BH", 26.2235, 50.5876),
    ("OM", 23.5880, 58.3829),
]
# Rough boxes so an iNat point is kept only when it still falls in that country.
GULF_BOX = {
    "SA": (34.4, 16.0, 55.7, 32.2),
    "AE": (51.5, 22.6, 56.4, 26.1),
    "QA": (50.7, 24.4, 51.7, 26.2),
    "KW": (46.5, 28.5, 48.5, 30.1),
    "BH": (50.3, 25.5, 50.8, 26.4),
    "OM": (52.0, 16.5, 59.9, 26.4),
}
COMMONS_CATS = {
    "interior": (
        "Category:Building interiors in Paris",
        "Category:Building interiors in France",
        "Category:Interiors of churches in France",
        "Category:Building interiors in London",
    ),
    "screenshot": (
        "Category:Geotagged screenshots",
        "Category:Screenshots with GPS",
    ),
}


def _get(url: str, params: dict | None = None, timeout: int = 40) -> dict:
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        dest.write_bytes(resp.read())


def _in_box(lon: float, lat: float, box: tuple[float, float, float, float]) -> bool:
    minx, miny, maxx, maxy = box
    return minx <= lon <= maxx and miny <= lat <= maxy


def _save_image(src: Path, dest: Path) -> str:
    im = Image.open(src)
    cropped, how = perspective_crop(im)
    cropped.thumbnail((640, 640))
    dest.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(dest, "JPEG", quality=80)
    src.unlink(missing_ok=True)
    return how


def panoramax(stratum: str, country: str, box: tuple[float, float, float, float], limit: int = 20) -> list[dict]:
    try:
        data = _get("https://api.panoramax.xyz/api/search", {
            "bbox": ",".join(str(v) for v in box), "limit": str(limit),
        })
    except OSError as exc:
        print(f"panoramax {stratum} {country}: {exc}", file=sys.stderr)
        return []
    out = []
    for feat in data.get("features") or []:
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        if not _in_box(lon, lat, box):
            continue
        assets = feat.get("assets") or {}
        href = ((assets.get("sd") or assets.get("thumb") or {}).get("href"))
        if not href:
            continue
        out.append({
            "id": f"panoramax:{feat.get('id')}",
            "stratum": stratum,
            "scene": "street",
            "country": country,
            "lat": lat,
            "lon": lon,
            "url": href,
            "source": "panoramax",
            "license": (feat.get("properties") or {}).get("license") or "",
        })
    return out


def inat_gulf(country: str, lat: float, lon: float) -> list[dict]:
    try:
        data = _get("https://api.inaturalist.org/v1/observations", {
            "lat": str(lat), "lng": str(lon), "radius": "30",
            "geo": "true", "has[]": "photos",
            "photo_license": "cc0,cc-by,cc-by-sa",
            "per_page": "30", "order_by": "observed_on", "order": "desc",
        })
    except OSError as exc:
        print(f"inat {country}: {exc}", file=sys.stderr)
        return []
    box = GULF_BOX[country]
    out = []
    for obs in data.get("results") or []:
        if obs.get("geoprivacy") in {"obscured", "private"} or obs.get("taxon_geoprivacy") in {"obscured", "private"}:
            continue
        loc = obs.get("location") or ""
        if "," not in loc:
            continue
        alat, alon = (float(x) for x in loc.split(",", 1))
        if not _in_box(alon, alat, box):
            continue
        photos = obs.get("photos") or []
        if not photos:
            continue
        url = (photos[0].get("url") or "").replace("square.", "medium.")
        if not url:
            continue
        out.append({
            "id": f"inat:{obs.get('id')}",
            "stratum": "gulf",
            "scene": "organism",
            "country": country,
            "lat": alat,
            "lon": alon,
            "url": url,
            "source": "inaturalist",
            "license": photos[0].get("license_code") or "",
        })
    return out


def commons_cat(stratum: str, title: str) -> list[dict]:
    api = "https://commons.wikimedia.org/w/api.php"
    try:
        data = _get(api, {
            "action": "query", "format": "json",
            "generator": "categorymembers", "gcmtitle": title, "gcmtype": "file", "gcmlimit": "50",
            "prop": "coordinates|imageinfo", "iiprop": "url|mime", "iiurlwidth": "640",
        })
    except OSError as exc:
        print(f"commons {title}: {exc}", file=sys.stderr)
        return []
    if data.get("error"):
        print(f"commons {title}: {data['error'].get('code')}", file=sys.stderr)
        return []
    out = []
    for page in (data.get("query") or {}).get("pages", {}).values():
        coords = page.get("coordinates") or []
        if not coords:
            continue
        info = (page.get("imageinfo") or [{}])[0]
        if not str(info.get("mime") or "").startswith("image/"):
            continue
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        out.append({
            "id": f"commons:{page.get('pageid')}",
            "stratum": stratum,
            "scene": stratum,
            "country": "",
            "lat": float(coords[0]["lat"]),
            "lon": float(coords[0]["lon"]),
            "url": url,
            "source": "commons",
            "license": "",
        })
    return out


def _cell(lat: float, lon: float) -> tuple[float, float]:
    return (round(lat, 3), round(lon, 3))


def _tiles(box: tuple[float, float, float, float], n: int = 2) -> list[tuple[float, float, float, float]]:
    minx, miny, maxx, maxy = box
    dx = (maxx - minx) / n
    dy = (maxy - miny) / n
    return [
        (minx + i * dx, miny + j * dy, minx + (i + 1) * dx, miny + (j + 1) * dy)
        for i in range(n) for j in range(n)
    ]


def gather() -> list[dict]:
    chosen: list[dict] = []
    seen_id: set[str] = set()
    seen_cell: set[tuple[str, float, float]] = set()

    def take(rows: list[dict], cap: int) -> None:
        for row in rows:
            if sum(1 for r in chosen if r["stratum"] == row["stratum"]) >= cap:
                return
            if row["id"] in seen_id:
                continue
            cell = (row["stratum"], *_cell(row["lat"], row["lon"]))
            if cell in seen_cell:
                continue
            seen_id.add(row["id"])
            seen_cell.add(cell)
            chosen.append(row)

    for stratum, country, box in PANO_SEEDS:
        if sum(1 for r in chosen if r["stratum"] == stratum) >= WANT[stratum]:
            continue
        for tile in _tiles(box, 2):
            if sum(1 for r in chosen if r["stratum"] == stratum) >= WANT[stratum]:
                break
            take(panoramax(stratum, country, tile), WANT[stratum])
            time.sleep(0.25)
    if sum(1 for r in chosen if r["stratum"] == "gulf") < WANT["gulf"]:
        for country, lat, lon in INAT_GULF:
            if sum(1 for r in chosen if r["stratum"] == "gulf") >= WANT["gulf"]:
                break
            take(inat_gulf(country, lat, lon), WANT["gulf"])
            time.sleep(0.4)
    for stratum, titles in COMMONS_CATS.items():
        if sum(1 for r in chosen if r["stratum"] == stratum) >= WANT[stratum]:
            continue
        for title in titles:
            time.sleep(3)
            take(commons_cat(stratum, title), WANT[stratum])
    # Top up to MIN_TOTAL from strata that already have real rows. Do not relabel.
    if len(chosen) < MIN_TOTAL:
        for stratum, country, box in PANO_SEEDS:
            if len(chosen) >= MIN_TOTAL:
                break
            if stratum == "gulf":
                continue
            take(panoramax(stratum, country, box, limit=50), 10_000)
            time.sleep(0.3)
    return chosen


def materialise(rows: list[dict]) -> list[dict]:
    photos = CORPUS / "photos"
    kept = []
    for i, row in enumerate(rows, 1):
        raw = photos / "_raw" / f"{i}.bin"
        dest = photos / row["stratum"] / f"{i}.jpg"
        raw.parent.mkdir(parents=True, exist_ok=True)
        try:
            _download(row["url"], raw)
            how = _save_image(raw, dest)
        except (OSError, Image.UnidentifiedImageError, ValueError) as exc:
            print(f"skip {row['id']}: {exc}", file=sys.stderr)
            raw.unlink(missing_ok=True)
            continue
        kept.append({
            **{k: row[k] for k in ("id", "stratum", "scene", "country", "lat", "lon", "source", "license")},
            "file": str(dest.relative_to(CORPUS)),
            "projection": how,
        })
        if i % 25 == 0:
            print(f"saved {len(kept)} / {i} fetched", file=sys.stderr)
    return kept


def main() -> int:
    repo = ROOT.resolve()
    if CORPUS == repo or repo in CORPUS.parents:
        print(f"SAQR_CORPUS must sit outside the repo ({CORPUS})", file=sys.stderr)
        return 2
    CORPUS.mkdir(parents=True, exist_ok=True)
    rows = gather()
    print(f"candidates {len(rows)}", file=sys.stderr)
    kept = materialise(rows)
    manifest = CORPUS / "manifest.jsonl"
    manifest.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept), encoding="utf-8")
    counts: dict[str, int] = {}
    scenes: dict[str, int] = {}
    for row in kept:
        counts[row["stratum"]] = counts.get(row["stratum"], 0) + 1
        scenes[row["scene"]] = scenes.get(row["scene"], 0) + 1
    summary = {"n": len(kept), "by_stratum": counts, "by_scene": scenes, "corpus": str(CORPUS)}
    (CORPUS / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary))
    if len(kept) < MIN_TOTAL:
        print(f"only {len(kept)} photos, need {MIN_TOTAL}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
