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

`uv.lock` resolved the `requirements.txt` pins at `c63e321`. Phase 7 (`fd22abc`) adds direct pins for `torch==2.15.0` and `streetlevel==0.12.13` and drops `pyfrpc`. `requirements.txt` still omits both, so `setup.sh` does not install them twice. The skill is cloned, not vendored.

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

Phase 7 supersedes the satellite layer and the reverse-search default. The sentences above are what phase 5 shipped.

Not in this phase: accounts for a multi-user server. Not closed: `H-GEOCLIP-01`, `H-RANK-01`, `B-PRIV-01`, `H-PROMPT-01`.

## Phase 6 — report

Status: DONE on `harden/commercial`.

| Commit | What landed | What it does not close |
|---|---|---|
| `1451911` | `GAP.md`. Eight Raven pages: find-region, find-street, find-property, live-intelligence, identify-car, verify-image, and FAQ are PARTIAL. short-term-rental image matching is MISSING. The 60-day figure is an estimate if a licensed listing-photo feed already exists. It is not a measured plan | No Raven feature was built. Person, plate, and private-place code were not touched |
| `aac3f09` | README rewritten to the code. The picker notes 10.9 km on the default and 8.7 km on the next row; the README does not call the default first. The map is not described as offline | `H-RANK-01` stays open. `OR_DEFAULT` was not changed |

At the end of phase 6, `B-PRIV-01` was still the code. Region and street stop at the city for a private person or a private home. Private-place replaced `SYSTEM` with `PRIVATE_NOTE` (`H-PROMPT-01`). Person and plate still ran. The README said that. It did not remove it. A later commit closed it by refusal. That close is withdrawn. The phase 7 table is the current state.

Still open: `H-GEOCLIP-01`, `H-RANK-01`. `H-PROMPT-01`'s dangling "rule above" sentence is gone in `d97e0b3`. Private-place mode still does not load `SYSTEM`. The ladder is in `PRIVATE_NOTE`.

## Phase 7 — measure, restore, and say what is not measured

Status: OPEN. Nothing here merges to `main`. The accuracy number does not exist yet.

Person mode does not identify a person unless `SAQR_PERSON_SEARCH=1`. Private-place mode pins a building only when `listing_tie` is true, and otherwise stops at the city. Plate mode still reads the characters and clears the owner field. The end-to-end score was not run.

| Item | Status |
|---|---|
| Corpus | 240 photos outside git (`SAQR_CORPUS`, default `/var/saqr-corpus`), manifest with the source coordinate. Strata: city 65, town 40, rural 40, gulf 40, interior 30, screenshot 25. Named screenshot categories returned 0 coordinates. `filetype:image screenshot haswbstatement:P1259` returned file coordinates. `upload.wikimedia.org` thumbs returned HTTP 429. A later pass used `commons.wikimedia.org/w/thumb.php` and added the 8 missing screenshots. Rows were not invented |
| Score | `bench/run_e2e.py flash` is every photo × 4 on `z-ai/glm-5.3-flash` and writes `flash.json` only when that tier is complete. That file is not the product number. `bench/run_e2e.py headline` is a stratified 50 on `anthropic/claude-opus-5.5` and writes `score.json` only when every selected photo has a row in every configuration. Neither file exists: both provider keys are empty. A GeoCLIP-only file is not this score. `H-RANK-01` stays open |
| H-GEOCLIP-01 | OPEN. The four-way run did not start. No key |
| H-RANK-01 | OPEN. No end-to-end figures. `OR_DEFAULT` was not re-ranked. The eye-benchmark notes stay as they are |
| Corpus gaps | `bench/fill_gaps.py` appends Commons files that themselves have coordinates. Interior is 30. Screenshot is 25. Rows were not invented |
| B-PRIV-01 | The refusal-only close is withdrawn. Default person mode still files `found: false` and calls nothing. `SAQR_PERSON_SEARCH=1` restores the model, web, Gravatar, and recon loop. Private mode keeps the evidence ladder and `listing_search`. A point is kept only when `listing_tie` is true. A school and a routine are not named. Plate characters are still read. The owner field is cleared |
| Bing satellite | Needs `SAQR_BING_KEY`. A Google key does not unlock it. ADR-013 |
| Wayback | Still refused. Not restored. ADR-013 |
| H-ESRI-01 | The phase 5 close (`7e23e6a`) deleted the layer. Restored in `d97e0b3`: Esri World Imagery, attribution, zoom clamped at 19, Wayback still refused. A browser on 2026-10-29 loaded zoom-19 JPEG tiles (HTTP 200) and `#mapErr` stayed hidden |
| Reverse search | ON by default again in `d97e0b3`. The form notice stays. A stored `false` in this browser stays off |
| H-PROMPT-01 | `d97e0b3` removed the dangling "rule above" sentence. Private-place text now stops at the city and is not a concatenation of `SYSTEM` |
| Tiles | ADR-012. If `tiles.openfreemap.org` fails, the map stops. No second free host |
| setup.sh | CPU index unless `nvidia-smi -L` succeeds, then cu130. `setup.bat` uses the same rule. ADR-014 |
| Docker | Not built. `docker` is not installed. `apt-get update` failed: `setgroups` not permitted, http/https method exit 112 |
| Browser | Clicked with Playwright Chromium 156.0.8078.4 against `127.0.0.1`. OpenFreeMap tiles HTTP 200. Satellite toggle reached Esri zoom 19 |
| uv.lock | CPU torch index. `pyexiv2==2.16.0` is in the lock and in `requirements.txt` because `streetlevel.exif` imports it. `pyfrpc`, `pytest`, `pytest-asyncio`, and `cython` stay out. The pytest job does not install torch. A separate job imports the CPU wheel |

`main` stays `4fbe65e`.

## Explicitly not scheduled

School naming and daily-routine naming stay out. Plate owner lookup stays out. Person search is `SAQR_PERSON_SEARCH=1`, not a new source. A private building pin is `listing_tie` only. I will not add a tool that names a school or a routine.
