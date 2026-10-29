#!/usr/bin/env python3
"""Append geotagged interior and screenshot rows. Does not relabel other strata.

Truth is a coordinate Commons returned on that file. A screenshot whose file
has no coordinates is skipped. This does not call Google Street View.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bench.build_corpus import CORPUS, _download, _get, _save_image, commons_cat  # noqa: E402

WANT = {"interior": 30, "screenshot": 25}
CATS = {
    "interior": (
        "Category:Building interiors in Paris",
        "Category:Building interiors in France",
        "Category:Building interiors in Germany",
        "Category:Building interiors in Italy",
        "Category:Building interiors in New York City",
        "Category:Building interiors in London",
        "Category:Interiors of churches in France",
    ),
    "screenshot": (
        "Category:Geotagged screenshots",
        "Category:Screenshots with GPS",
        "Category:Screenshots of OpenStreetMap",
        "Category:Screenshots of mobile phones",
    ),
}


def _load() -> list[dict]:
    path = CORPUS / "manifest.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def search_screenshots(limit: int = 50, offset: int = 0) -> list[dict]:
    """Commons files the search calls screenshots and that carry P1259 (point of view)."""
    api = "https://commons.wikimedia.org/w/api.php"
    try:
        data = _get(api, {
            "action": "query", "format": "json",
            "generator": "search",
            "gsrsearch": "filetype:image screenshot haswbstatement:P1259",
            "gsrnamespace": "6", "gsrlimit": str(limit), "gsroffset": str(offset),
            "prop": "coordinates|imageinfo", "iiprop": "url|mime", "iiurlwidth": "640",
        })
    except OSError as exc:
        print(f"commons screenshot search: {exc}", file=sys.stderr)
        return []
    if data.get("error"):
        print(f"commons screenshot search: {data['error'].get('code')}", file=sys.stderr)
        return []
    out = []
    for page in (data.get("query") or {}).get("pages", {}).values():
        coords = page.get("coordinates") or []
        info = (page.get("imageinfo") or [{}])[0]
        if not coords or not str(info.get("mime") or "").startswith("image/"):
            continue
        title = str(page.get("title") or "")
        fname = title.split(":", 1)[-1] if ":" in title else title
        thumb_php = ""
        if fname:
            thumb_php = "https://commons.wikimedia.org/w/thumb.php?" + urllib.parse.urlencode({"f": fname, "w": "640"})
        special = ""
        if fname:
            special = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(fname) + "?width=640"
        upload = info.get("thumburl") or ""
        url = thumb_php or special or upload
        if not url:
            continue
        out.append({
            "id": f"commons:{page.get('pageid')}",
            "stratum": "screenshot",
            "scene": "screenshot",
            "country": "",
            "lat": float(coords[0]["lat"]),
            "lon": float(coords[0]["lon"]),
            "url": url,
            "fallback": special if special and special != url else upload,
            "source": "commons",
            "license": "",
        })
    return out


def _store(cand: dict, have: set[str], added: list[dict]) -> bool:
    if cand["id"] in have:
        return False
    dest = CORPUS / "photos" / cand["stratum"] / f"{cand['id'].replace(':', '-')}.jpg"
    raw = CORPUS / "photos" / "_raw" / f"{cand['id'].replace(':', '-')}.bin"
    raw.parent.mkdir(parents=True, exist_ok=True)
    time.sleep(2)
    urls = [cand["url"]]
    fallback = cand.get("fallback") or ""
    if fallback and fallback not in urls:
        urls.append(fallback)
    last = ""
    for i, url in enumerate(urls):
        if i:
            time.sleep(45)
        try:
            _download(url, raw)
            how = _save_image(raw, dest)
            last = ""
            break
        except (OSError, ValueError) as exc:
            last = str(exc)
            cand["_fail"] = last
            print(f"skip {cand['id']}: {last[:180]}", file=sys.stderr)
            if "429" not in last:
                return False
    if last:
        return False
    added.append({
        "id": cand["id"],
        "stratum": cand["stratum"],
        "scene": cand["stratum"],
        "country": cand.get("country") or "",
        "lat": cand["lat"],
        "lon": cand["lon"],
        "source": "commons",
        "license": "",
        "file": str(dest.relative_to(CORPUS)),
        "projection": how,
        "truth": "file-coordinates",
    })
    have.add(cand["id"])
    return True


def main() -> int:
    rows = _load()
    have = {r["id"] for r in rows}
    added: list[dict] = []
    for stratum, titles in CATS.items():
        def _need() -> int:
            return WANT[stratum] - sum(1 for r in rows if r["stratum"] == stratum) - sum(1 for r in added if r["stratum"] == stratum)

        if _need() <= 0:
            continue
        for title in titles:
            if _need() <= 0:
                break
            time.sleep(3)
            found = commons_cat(stratum, title)
            print(f"{title} coords={len(found)}", file=sys.stderr)
            for cand in found:
                if _need() <= 0:
                    break
                _store(cand, have, added)
        if stratum == "screenshot" and _need() > 0:
            for offset in (0, 20, 40, 60):
                if _need() <= 0:
                    break
                time.sleep(5)
                found = search_screenshots(20, offset)
                print(f"screenshot P1259 offset={offset} coords={len(found)}", file=sys.stderr)
                if not found:
                    break
                for cand in found:
                    if _need() <= 0:
                        break
                    _store(cand, have, added)
    if added:
        with (CORPUS / "manifest.jsonl").open("a", encoding="utf-8") as fh:
            for row in added:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    all_rows = rows + added
    counts: dict[str, int] = {}
    for row in all_rows:
        counts[row["stratum"]] = counts.get(row["stratum"], 0) + 1
    summary = {"n": len(all_rows), "by_stratum": counts, "corpus": str(CORPUS), "added": len(added)}
    (CORPUS / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary))
    short = {k: counts.get(k, 0) for k in WANT if counts.get(k, 0) < WANT[k]}
    if short:
        print(f"short of target {short}. screenshot rows were not invented.", file=sys.stderr)
        return 2
    return 0


def retry_screenshots() -> int:
    """One slower pass. thumbs come from commons.wikimedia.org, not upload.wikimedia.org."""
    rows = _load()
    have = {r["id"] for r in rows}
    added: list[dict] = []

    def need() -> int:
        return WANT["screenshot"] - sum(1 for r in rows if r["stratum"] == "screenshot") - len([r for r in added if r["stratum"] == "screenshot"])

    print(f"retry need {need()}", file=sys.stderr)
    if need() <= 0:
        return 0
    time.sleep(40)
    streak = 0
    for offset in (0, 20, 40, 60, 80, 100, 120, 140):
        if need() <= 0 or streak >= 2:
            break
        time.sleep(10)
        found = search_screenshots(20, offset)
        print(f"retry offset={offset} coords={len(found)}", file=sys.stderr)
        if not found:
            break
        for cand in found:
            if need() <= 0 or streak >= 2:
                break
            if cand["id"] in have:
                continue
            time.sleep(18)
            if _store(cand, have, added):
                streak = 0
                print(f"saved {cand['id']} left {need()}", file=sys.stderr)
            elif "429" in str(cand.get("_fail") or ""):
                streak += 1
            else:
                streak = 0
    if added:
        with (CORPUS / "manifest.jsonl").open("a", encoding="utf-8") as fh:
            for row in added:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    all_rows = _load()
    counts: dict[str, int] = {}
    for row in all_rows:
        counts[row["stratum"]] = counts.get(row["stratum"], 0) + 1
    summary = {"n": len(all_rows), "by_stratum": counts, "corpus": str(CORPUS), "added": len(added)}
    (CORPUS / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary))
    if counts.get("screenshot", 0) < WANT["screenshot"]:
        print(f"short of target screenshot {counts.get('screenshot', 0)}. screenshot rows were not invented.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(retry_screenshots() if "--retry-thumbs" in sys.argv else main())
