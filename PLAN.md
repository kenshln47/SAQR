# SAQR plan

Source audit: `AUDIT.md`, tree `427ea54102bb04588cc4eb63bbcd90f0b2be80ed`.
Order is fixed. A phase ends only when `AGENTS.md` §3 holds for the findings it claims to close.

## Phase 0 — recon

Status: DONE when this file and `AUDIT.md` are on `main`.
No code changes. Findings opened: every ID in `AUDIT.md`. Findings closed: none.

## Phase 1 — blockers that are licensing

Do these, in order, one commit each. Do not touch person search, plate-owner lookup, or private-place targeting (`B-PRIV-01`, `H-PROMPT-01`).

| Order | ID | Work |
|---|---|---|
| 1 | B-LIC-01 | `LICENSE` (proprietary, all rights reserved — commercial product, not a sample app), `NOTICE`, `THIRD_PARTY.md`, one-line ADR in `DECISIONS.md`. |
| 2 | B-NC-01 | Commercial default skips the StreetCLIP/world prior. Opt-in only via `SAQR_ALLOW_NC_MODELS=1`. README states that. |
| 3 | B-GGL-01 | Default panorama provider `mapillary`. Google Street View and Google tiles require `SAQR_GOOGLE_KEY` or `GOOGLE_MAPS_API_KEY`. |
| 4 | M-BING-01 | Same key gate for `apple`, `bing`, `yandex`, or drop them from the tool description. Done in the Google commit if it stays a one-line extension. |

Leave open: `B-PRIV-01` (will not implement), `H-ESRI-01` (separate tile vendor; do not silently rebadge Esri as fine).

Done when: `pytest` green, `ruff check` clean, README matches the new defaults, `PLAN.md` lists the commit hashes.

## Phase 2 — accuracy

`H-RANK-01`. Add `bench/` (300–500 held-out photos, stratified). Metrics: median km, % <1 km, % <25 km, % country-correct, ECE for the model's confidence and radius. Wire to geoint `photo_session.py` + `bench.py` once that skill is vendored (phase 4). CI gate. Confirm/dismiss on a candidate writes ground truth into the case. Re-rank `OR_DEFAULT` from that run, not from the October table.

## Phase 3 — reliability

`H-SSE-01`, `H-LOAD-01`, `H-POOL-01`, `H-ID-01`, `M-LOCK-01`, `M-CAT-01`, `M-PRUNE-01`.
In-memory case cache, event index, bounded pool, per-case cost in the UI, token accounting instead of "6 images and 20k characters".

## Phase 4 — packaging

`M-TEST-01`, `M-PKG-01`, `M-GEOINT-01`, `M-IMPORT-01`, `L-PHOTO-01`.
`pyproject.toml`, `uv.lock`, pytest, ruff, GitHub Actions, Dockerfile, `scripts/setup.sh` next to the `.bat` files. Vendor or fetch the geoint skill so a clone runs. Stop creating directories and failing cases at import time.

The phase 1 tests may add the smallest pytest/ruff entry so §3 can pass before this phase finishes. That does not close phase 4.

## Phase 5 — product

`H-NET-01`, `H-ESRI-01`, `M-REV-01`, `L-REPORT-FONT`, `L-CSP-01`.
Privacy policy, ToS, retention. Reverse search default off; the Yandex/Baidu sentence stays. Vendor fonts. Replace the Esri raster. Candidate states: confirmed / possible / dismissed.

Not in this phase: accounts for a multi-user server, until the single-user licence gates above are actually true.

## Phase 6 — report

`GAP.md` against Raven's public pages: find-region, find-street, find-property, short-term-rental, live-intelligence, identify-car, verify-image, FAQ. Each is HAVE / PARTIAL / MISSING with a day cost. README rewritten to what the code does, including the contradiction in `B-PRIV-01` if that code is still present.

## Explicitly not scheduled

`B-PRIV-01`, `H-PROMPT-01`. Identifying a private person from a photo, email, phone, or name, reading a plate to find an owner, and pinning a private home, school, or daily routine stay as they are in the tree. I will not extend them.
