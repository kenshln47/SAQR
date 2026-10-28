# SAQR plan

Source audit: `AUDIT.md`, tree `427ea54102bb04588cc4eb63bbcd90f0b2be80ed`.
Order is fixed. A phase ends only when `AGENTS.md` §3 holds for the findings it claims to close.

## Phase 0 — recon

Status: DONE in `0a384b9` (`docs: phase 0 audit and plan`).
No code changes. Findings opened: every ID in `AUDIT.md`. Findings closed: none.

## Phase 1 — blockers that are licensing

| Order | ID | Status |
|---|---|---|
| 1 | B-LIC-01 | DONE `d31a166` |
| 2 | B-NC-01 | DONE `a111837` |
| 3 | B-GGL-01 | DONE `7018f5f` |
| 4 | M-BING-01 | DONE `7018f5f` (same commit: one key does not unlock the other closed providers) |

Opened on this branch, not closed: `H-GEOCLIP-01`. `--skip calib,prior` also drops GeoCLIP (MIT). Phase 2 measures it. A full skip is not an acceptable end state if that cost is material.

Left open on purpose: `B-PRIV-01`, `H-PROMPT-01`. The README now describes those modes as they are. The code was not extended.
Left open because it is a different vendor: `H-ESRI-01`.

## Phase 2 — accuracy

`H-RANK-01`, `H-GEOCLIP-01`.
Score median km, % <1 km, % <25 km, % country-correct, and ECE for confidence and for the stated radius.
Three prior settings: off, GeoCLIP only (`prior.py --models geoclip`), StreetCLIP+GeoCLIP (non-commercial opt-in).
If GeoCLIP-only is close to both models, keep StreetCLIP out. If the gap is large, the choice is a commercial StreetCLIP licence or another permissive model, not a silent skip.
Wire scoring through GeoInt `bench.py score` and ground truth through `photo_session.py truth`.
Confirm / dismiss on a candidate writes that truth into the case.
Do not re-rank `OR_DEFAULT` from the October table. Re-rank only from a run this bench actually produces.
`bench.py make-streetview` fetches keyless Google panoramas. Do not use it to build the corpus.

## Phase 3 — reliability

`H-SSE-01`, `H-LOAD-01`, `H-POOL-01`, `H-ID-01`, `M-LOCK-01`, `M-CAT-01`, `M-PRUNE-01`.
In-memory case cache, event index, bounded pool, per-case cost in the UI, token accounting instead of "6 images and 20k characters".

## Phase 4 — packaging

`M-TEST-01`, `M-PKG-01`, `M-GEOINT-01`, `M-IMPORT-01`, `L-PHOTO-01`.
`pyproject.toml` already holds pytest and ruff settings from phase 1. Still missing: `uv.lock`, the dependency list, GitHub Actions, Dockerfile, `scripts/setup.sh` next to the `.bat` files. Vendor or fetch the geoint skill so a clone runs. Stop creating directories and failing cases at import time.

## Phase 5 — product

`H-NET-01`, `H-ESRI-01`, `M-REV-01`, `L-REPORT-FONT`, `L-CSP-01`.
Privacy policy, ToS, retention. Reverse search default off; the Yandex/Baidu sentence stays. Vendor fonts. Replace the Esri raster. Candidate states: confirmed / possible / dismissed.

Not in this phase: accounts for a multi-user server, until the single-user licence gates above are actually true.

## Phase 6 — report

`GAP.md` against Raven's public pages: find-region, find-street, find-property, short-term-rental, live-intelligence, identify-car, verify-image, FAQ. Each is HAVE / PARTIAL / MISSING with a day cost. README rewritten to what the code does, including the contradiction in `B-PRIV-01` if that code is still present.

## Explicitly not scheduled

`B-PRIV-01`, `H-PROMPT-01`. Identifying a private person from a photo, email, phone, or name, reading a plate to find an owner, and pinning a private home, school, or daily routine stay as they are in the tree. I will not extend them.
