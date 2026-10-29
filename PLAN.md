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

`B-PRIV-01` is still the code. Region and street stop at the city for a private person or a private home. Private-place replaces `SYSTEM` with `PRIVATE_NOTE` (`H-PROMPT-01`). Person and plate still run. The README says that. It does not remove it.

Still open: `H-GEOCLIP-01`, `H-RANK-01`, `B-PRIV-01`. `H-PROMPT-01`'s dangling "rule above" sentence is gone in `d97e0b3`. Private-place mode still does not load `SYSTEM`, and it still targets a building, a school, and a routine. That was not removed.

## Phase 7 — measure, restore, and say what is not measured

Status: OPEN. Nothing here merges to `main`. The accuracy number does not exist yet.

The product still identifies a person from a photo, email, phone, or name, still reads a plate, and still can pin a private place. This phase does not remove that.

| Item | Status |
|---|---|
| Corpus | 202 photos outside git (`SAQR_CORPUS`, default `/var/saqr-corpus`), manifest with the source coordinate. Strata: city 65, town 40, rural 40, gulf 40, interior 17, screenshot 0. Screenshot categories that were fetched had no coordinates. Commons geosearch and Wikidata SPARQL did not return a usable set (cirrussearch busy, HTTP 429). Not invented |
| Score | `bench/run_score.py` is the local GeoCLIP prior only (`95b0818`). `score.json` is not written. Do not quote a median from a partial `geoclip_detail.jsonl`. This is not the tool-using agent and not a vision-LLM rank |
| H-GEOCLIP-01 | OPEN. StreetCLIP has not been run on this corpus. RAM is about 4 GB; it waits until GeoCLIP is not resident |
| H-RANK-01 | OPEN. No provider key. `OR_DEFAULT` was not re-ranked. The picker still says 10.9 km on the default and 8.7 km on the next row |
| H-ESRI-01 | The phase 5 close (`7e23e6a`) deleted the layer. Restored in `d97e0b3`: Esri World Imagery, attribution, zoom clamped at 19, Wayback still refused. A browser on 2026-10-29 loaded zoom-19 JPEG tiles (HTTP 200) and `#mapErr` stayed hidden |
| Reverse search | ON by default again in `d97e0b3`. The form notice stays. A stored `false` in this browser stays off |
| H-PROMPT-01 | Prompt text rewritten in `d97e0b3`. Plate: do not guess an owner. Person: `found` needs a second tie; a same-name hit is unverified. `PRIVATE_NOTE` stands alone. `SYSTEM` is not concatenated onto it. `B-PRIV-01` stays open |
| Tiles | ADR-012. If `tiles.openfreemap.org` fails, the map stops. No second free host. Replacement is a paid vector endpoint or a self-hosted OpenMapTiles/Planetiler/Protomaps server, by editing `web/vendor/ofm-dark.json` |
| setup.sh | Ran. Exit 0. It installed `torch 2.15.0+cu132` and `nvidia-*` wheels. `torch.cuda.is_available()` was false. The script comment had said CPU. `fd22abc` corrects the comment. It does not add a CPU index |
| Docker | Not built. `docker` is not installed. `apt-get update` failed: `setgroups` not permitted, http/https method exit 112 |
| Browser | Clicked with Playwright Chromium 156.0.8078.4 against `127.0.0.1`. OpenFreeMap tiles HTTP 200. Satellite toggle reached Esri zoom 19. The server was then stopped |
| uv.lock | `fd22abc`. `torch==2.15.0` and `streetlevel==0.12.13` are direct pins. `pyfrpc` is not in the lock. They are still not in `requirements.txt`, and not in `.github/workflows/test.yml` |

`main` stays `4fbe65e`.

## Explicitly not scheduled

`B-PRIV-01`. Identifying a private person from a photo, email, phone, or name, reading a plate, and pinning a private home, school, or daily routine stay in the tree. Phase 7 rewrote the prompt text (`d97e0b3`) and did not extend those paths. I will not add a tool, a test, or a prompt that makes that targeting better.
