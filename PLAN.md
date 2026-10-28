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
Left for a later phase at the time: `H-ESRI-01`. Closed in phase 5 (`7e23e6a`).

## Phase 2 — accuracy

Status: PARTIAL. Not done. `H-GEOCLIP-01` and `H-RANK-01` stay open.

| Commit | What landed | What it does not close |
|---|---|---|
| `53370dc` | Commercial path calls `prior.py --models geoclip` after `--skip calib,prior` | No kilometre comparison against StreetCLIP or against prior-off |
| `dcd8ba2` | `app/benchscore.py`: median km, share under 1 km, share under 25 km, country accuracy, ECE for confidence and for the stated radius. CI runs pytest and ruff on pillow, pytest, and ruff only | No corpus. Commons geosearch on 2026-10-28 returned `cirrussearch-too-busy-error`. `make-streetview` was not used |
| `2d40308` | Confirm writes `truth` and `truth.json`. Dismiss does not replace an existing truth | One analyst label is not a bench |

`OR_DEFAULT` was not re-ranked. Do not treat any October table figure as a new measurement.

## Phase 3 — reliability

Status: DONE on `harden/commercial`.

| ID | Status |
|---|---|
| H-ID-01 | DONE `93d0bb1` |
| H-LOAD-01 | DONE `0acb481` |
| H-SSE-01 | DONE `af60fae` |
| M-LOCK-01 | DONE `d3e6562` |
| H-POOL-01 | DONE `3991a06` |
| M-CAT-01 | DONE `648b7bb` |
| M-PRUNE-01 | DONE `b7786c1` |

The event tail is an in-memory index. `case.json` is cached after the first read. Case ids cannot be `.`, `..`, or a symlink that leaves `CASES_DIR`. Each case has its own lock. `catalog()` does not hold its lock across the request, and a failed refresh keeps the previous list. At most `SAQR_WORKERS` analyses run (default 2). Context is a token budget, not a fixed image count.

## Phase 4 — packaging

Status: DONE on `harden/commercial`.

| ID | Status |
|---|---|
| M-IMPORT-01 | DONE `93e3ee6` |
| L-PHOTO-01 | DONE `8770f47` |
| M-TEST-01 | DONE `88747fb` (pytest, ruff, and the workflow were already in the tree; this commit locks them in) |
| M-PKG-01 | DONE `c63e321` |
| M-GEOINT-01 | DONE `d5414fd` |

`uv.lock` resolves the `requirements.txt` pins. Torch and `streetlevel` stay outside that lock: setup installs torch itself, and streetlevel with `--no-deps`, same as `setup.bat`. The skill is cloned, not vendored.

## Phase 5 — product

Status: DONE on `harden/commercial`.

| ID | Status |
|---|---|
| M-REV-01 | DONE `584f03a` |
| H-NET-01 | DONE `13a4c1c` |
| H-ESRI-01 | DONE `7e23e6a` |
| L-REPORT-FONT | DONE `cbaf91f` |
| L-CSP-01 | DONE `dda66a8` |

Reverse search defaults off. The Yandex/Baidu sentence stays. Fonts are local. The style JSON is local and the tiles are OpenFreeMap. The satellite toggle is NASA GIBS Blue Marble, native zoom 8. Esri and Wayback are refused. `possible` does not write truth (`266d2b7`). Privacy, terms, and retention are `46ada21`.

Not in this phase: accounts for a multi-user server. Not closed: `H-GEOCLIP-01`, `H-RANK-01`, `B-PRIV-01`, `H-PROMPT-01`.

## Phase 6 — report

`GAP.md` against Raven's public pages: find-region, find-street, find-property, short-term-rental, live-intelligence, identify-car, verify-image, FAQ. Each is HAVE / PARTIAL / MISSING with a day cost. README rewritten to what the code does, including the contradiction in `B-PRIV-01` if that code is still present.

## Explicitly not scheduled

`B-PRIV-01`, `H-PROMPT-01`. Identifying a private person from a photo, email, phone, or name, reading a plate to find an owner, and pinning a private home, school, or daily routine stay as they are in the tree. I will not extend them.
