# Bench

This directory does not contain a photo corpus.

SAQR's accuracy is not measured yet. `app/benchscore.py` scores rows you already have:
median km, share within 1 km, share within 25 km, country accuracy, and ECE for the
stated confidence (against a country hit) and for the stated radius (`error_km <= radius_km`).
Confidence words map to high 0.85, medium 0.55, low 0.25. The module does not download
anything and does not shell out to GeoInt.

GeoInt `scripts/bench.py score preds.json --truth truth.json` reports the same distance
and country figures, not ECE. Use it when a real `preds.json` and `truth.json` exist.
`scripts/photo_session.py truth` is the per-session shape (lat, lon, country, error_km).
An analyst confirmation in the UI writes `truth.json` inside the case folder. That is one
labelled case, not a bench.

Do not build the corpus with `bench.py make-streetview`. That command fetches Google
Street View without a key, which SAQR refuses.

Photos for a later run live outside git (`SAQR_CORPUS`, default `/var/saqr-corpus`).
`run_e2e.py flash` is every photo times four configurations on `z-ai/glm-5.3-flash`.
It writes `flash.json` only when that tier finishes. That file is not the product number.
`run_e2e.py headline` is a stratified 50 on `anthropic/claude-opus-5.5` and writes
`score.json` only when every selected row exists. `run_score.py` is a GeoCLIP-only
local prior and is not this score. Neither score has been written. Screenshot is 25.
`upload.wikimedia.org` returned HTTP 429. `commons.wikimedia.org/w/thumb.php` supplied the last 8. Rows were not invented.

A Commons geosearch on 2026-10-28 returned HTTP 200 with `cirrussearch-too-busy-error`.
`fetch_commons.py` retries that query and exits without writing a file when the API
is busy or empty. Do not commit a hand-written manifest.
