#!/usr/bin/env python3
"""Fetch Wikimedia Commons geosearch metadata. Never invents a row.

Writes bench/manifest.jsonl only when the API returns pages. A busy or empty
response leaves the tree unchanged and exits 2. This is not the 300-photo
corpus, and it does not call Google Street View.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "manifest.jsonl"
API = "https://commons.wikimedia.org/w/api.php"
# Seeds only. A successful response is still a sample, not a stratified bench.
SEEDS = (
    ("city", "24.7136|46.6753"),
    ("town", "26.3260|43.9750"),
    ("rural", "25.3000|49.6000"),
)


def query(coord: str) -> dict:
    params = {
        "action": "query", "format": "json", "generator": "geosearch",
        "ggscoord": coord, "ggsradius": "10000", "ggslimit": "20", "ggsnamespace": "6",
        "prop": "imageinfo", "iiprop": "url|mime",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "SAQR-bench/1.0 (local; corpus retry)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    rows = []
    for kind, coord in SEEDS:
        try:
            payload = query(coord)
        except OSError as exc:
            print(f"{kind}: request failed ({exc})", file=sys.stderr)
            continue
        if payload.get("error"):
            print(f"{kind}: {payload['error'].get('code')}", file=sys.stderr)
            continue
        pages = (payload.get("query") or {}).get("pages") or {}
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            if not page.get("pageid") or "lat" not in page or "lon" not in page or not info.get("url"):
                continue
            rows.append({
                "pageid": page["pageid"], "title": page.get("title"), "kind": kind,
                "lat": page["lat"], "lon": page["lon"], "url": info["url"], "mime": info.get("mime"),
            })
    if not rows:
        print("no rows written", file=sys.stderr)
        return 2
    OUT.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    print(f"wrote {len(rows)} rows to {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
