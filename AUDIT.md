# SAQR audit

Read-only pass of `main` at `427ea54102bb04588cc4eb63bbcd90f0b2be80ed` (2026-10-28).
Every `file:line` below was read in that tree. `py_compile` of `app/*.py` succeeded.
The server was not booted: this machine has no `uv`, no `.venv`, and no geoint skill at
`~/.claude/skills/geoint`. Pinned `fastapi==0.162.0`, `uvicorn==0.54.0`, `anthropic==2.3.0`,
`numpy==2.5.2`, and `opencv-python-headless==5.0.0.93` all resolve on PyPI.

## BLOCKER

### [B-LIC-01] BLOCKER — no licence for SAQR's own code

`LICENSE` is absent (repo root listing: `.env.example`, `.gitignore`, `AGENTS.md`, `README.md`, `app/`, `requirements.txt`, `run.bat`, `setup.bat`, `web/`). Vendored notices exist only inside `web/vendor/`.

What breaks: a buyer, a redistributor, or a host cannot tell what they are allowed to copy. BSD-3 (MapLibre) and BSD-2 (rtl-text) require their notices to travel with the binary. Shipping without `LICENSE` / `NOTICE` fails that the moment the app is given to anyone else.

Fix: add `LICENSE` for SAQR's code, plus `NOTICE` and `THIRD_PARTY.md` that name every vendored and downloaded component.

Effort: S. Verify: those three files exist and name MapLibre GL JS 4.7.1, mapbox-gl-rtl-text 0.2.3, and the non-commercial models.

### [B-NC-01] BLOCKER — StreetCLIP weights are CC-BY-NC-4.0 and the product calls them

StreetCLIP is not in this repo. The local prior is still part of the product:

```249:249:app/agent.py
                            "radius_km": 300, "reason": "ترتيب GeoCLIP و StreetCLIP (منطقة بداية، متوسط الخطأ ~270 كم)",
```

```320:321:app/agent.py
                     "summary": "وضع محلي بدون ذكاء اصطناعي: هذا تخمين نماذج التعرف المحلية فقط (GeoCLIP + StreetCLIP). "
                                "أضف مفتاح OpenRouter أو Anthropic من الإعدادات عشان يشتغل التحليل الكامل والتحقق.",
```

`tools.recon` always runs `recon.py` (`app/tools.py:79-84`) with `--skip calib` only. README line 40 says the no-key path is "the GeoCLIP/StreetCLIP world prior". Hugging Face `geolocal/StreetCLIP` is **CC-BY-NC-4.0**. Its model card also says geolocating private images is out of scope. SAQR's purpose is geolocating the user's photos, including private places (`app/agent.py:53-66`).

GeoCLIP and MegaLoc licences were not in this tree. Treat them as unverified until the geoint prior script is in-repo.

What breaks: any paid or public deployment that lets recon download or run StreetCLIP is a non-commercial-licence breach, not a grey area.

Fix: default commercial path must not request the StreetCLIP prior. Isolate behind an explicit opt-in (`SAQR_ALLOW_NC_MODELS=1`) and say so in `THIRD_PARTY.md` and the README. Do not vendor the weights.

Effort: M. Verify: with the env var unset, the `recon.py` argv contains a skip for the prior; with it set, the skip is absent. README no longer says the default local prior is StreetCLIP.

### [B-GGL-01] BLOCKER — Google Street View and Google tiles are fetched with no key

Sweep default is the string `"google"`:

```143:148:app/tools.py
def streetview_sweep(case: Case, lat: float, lon: float, radius_m: int = 3000, provider: str = "google") -> ToolOut:
    """List every panorama in a small area, index them, rank by visual similarity to the photo (MegaLoc)."""
    radius_m = int(min(max(radius_m, 200), 4400))
    tag = f"sw_{provider}_{lat:.3f}_{lon:.3f}_{radius_m}".replace("-", "m").replace(".", "p")
    rc, out = run_script(case, "pano.py", ["list", "--provider", provider, "--near", _ll(lat, lon),
```

The agent passes that default again at `app/agent.py:206`. `streetview_near` and `streetview_views` always call `gsv.py` (`app/tools.py:126-136`) and the tool text says "official Google Street View" (`app/agent.py:82-85`). Satellite accepts `google` and `google-hybrid` with no key check (`app/tools.py:28`, `app/tools.py:165-166`). README lines 92-93 admit this is "fine for personal use, not for a public service."

What breaks: a commercial service that scrapes Street View or Google tiles without a billed key violates Google's terms the first time a customer runs Find Street.

Fix: default panorama provider `mapillary` (Kartaview and Panoramax stay selectable). Refuse `provider=google` and satellite sources `google` / `google-hybrid` unless `SAQR_GOOGLE_KEY` or `GOOGLE_MAPS_API_KEY` is set, and pass that key through to the subprocess. Same gate for `streetview_near` and `streetview_views`.

Effort: M. Verify: unit tests for the default provider and for the refusal when no key is set.

Closed in `7018f5f` for the Google/Apple/Bing/Yandex gate. Esri is still `H-ESRI-01`.

### [H-GEOCLIP-01] HIGH — skipping `prior` drops GeoCLIP (MIT), not only StreetCLIP

`recon_skip_arg()` returns `calib,prior` whenever `SAQR_ALLOW_NC_MODELS` is unset (`app/licensing.py`). GeoInt `scripts/recon.py` runs `prior.py` as one step (`prior.py` default `--models streetclip,geoclip`). GeoCLIP is MIT. StreetCLIP is the only non-commercial weight in that step. The commercial skip removes both, so the no-key path has no local coordinate at all (`app/agent.py` errors when `prior.json` has no lat).

What breaks: a licence fix shipped as a silent accuracy regression. Trigger: any commercial run, including one with an API key, because recon never writes `work/recon/prior/prior.json`.

Fix: measure prior-off vs GeoCLIP-only vs StreetCLIP+GeoCLIP in phase 2. If the gap is material, buy a StreetCLIP licence or call `prior.py --models geoclip` and keep StreetCLIP out. Do not leave the full skip in place once that measurement exists.

The commercial follow-up is now `prior.py --models geoclip` after `--skip calib,prior` (`app/licensing.py` `prior_followup_args`, `app/tools.py` `recon`). StreetCLIP still loads only when `SAQR_ALLOW_NC_MODELS=1`. That is the permissive swap, not a measurement. No SAQR corpus has been scored, so this finding stays open. Commons geosearch on 2026-10-28 returned `cirrussearch-too-busy-error`. `bench.py make-streetview` is not an acceptable corpus.

Effort: M. Verify: a bench score with the three prediction files, and a commercial argv that still requests GeoCLIP. The argv check is in `tests/test_recon_followup.py`. The score file does not exist yet.


### [B-PRIV-01] BLOCKER — shipped modules contradict the published limits and identify private people

README lines 87-91 say private homes stop at city level, and that a plate number is never read, searched, or recorded. The code does the opposite.

Private-place mode tells the model to pin the building, match schools, name a daily routine, and search the family plate (`app/agent.py:53-66`). Person mode takes a photo, email, phone, or name and files a real person's accounts (`app/identify.py:66-86`, `app/server.py:29`, `web/index.html:197`). Plate mode reads the characters and searches the number for an owner (`app/identify.py:88-102`, `web/index.html:198`). `cases._blank_png` exists specifically "for a text-only case (person search by email / phone / name)" (`app/cases.py:151-152`).

What breaks: the README is false, and the product as shipped compiles identifying information on private people and private places. I will not add, test, or refine those paths.

Fix that I will not do here: leave the modules untouched. Do not wire them into new tests, prompts, or tools.

Effort: not estimated. Verify: `git diff` on `app/identify.py`, `PRIVATE_NOTE`, and the person/plate UI is empty after later phases.

## HIGH

### [H-PROMPT-01] HIGH — private mode drops the geolocation system prompt

```378:378:app/agent.py
    system = PRIVATE_NOTE if mode == "private" else SYSTEM
```

Same assignment at `app/agent.py:447`. `PRIVATE_NOTE` says "the stop at city level rule above is relaxed" (`app/agent.py:54`) but `SYSTEM` is not included, so the method, the tool discipline, and the plate ban never reach the model. Trigger: mode `private`.

Fix: not in the licence phase, and not by me if the fix is to make private-home targeting work better. Recorded so it is not mistaken for an intentional prompt.

Effort: S. Verify: unread until a later change; do not "fix" by concatenating the two prompts.

### [H-SSE-01] HIGH — every stream re-reads the whole log

`stream` loops `case.events(sent)` then `asyncio.sleep(0.6)` (`app/server.py:258-273`). `events()` holds the process lock and reads the entire `events.jsonl` (`app/cases.py:107-118`). Trigger: two long Street runs open in two browsers.

Fix (phase 3): in-memory ring plus an index, tail from `sent`.

Effort: M. Verify: a test that appends N events and streams from index N-1 without asserting a full-file read in the hot path.

### [H-LOAD-01] HIGH — `Case.load()` hits disk on every poll

`load()` reads and parses `case.json` (`app/cases.py:81-87`). `cancelled()` and `running()` call it (`app/cases.py:140-144`). The agent calls `cancelled()` every turn (`app/agent.py:352-356`). `add_candidate` loads again (`app/cases.py:120-128`). Trigger: a 40-turn street run.

Fix (phase 3): cache the dict, invalidate on `_save`.

Effort: S. Verify: a test that two `load()` calls after one `update` see the new field, and a counter shows one read.

### [H-POOL-01] HIGH — one unbounded thread per case, subprocesses up to an hour

```49:56:app/server.py
def _start(case: cases.Case, mode: str) -> None:
    ...
    threading.Thread(target=target, daemon=True, name=f"case-{case.id}").start()
```

`run_script` timeouts are 900s default, 1800s recon, 3600s sweep index (`app/tools.py:39`, `app/tools.py:84`, `app/tools.py:153`). Nothing queues or caps them. Trigger: a few Find Street uploads.

Fix (phase 3): bounded executor and a per-case cost meter.

Effort: M. Verify: the (N+1)th submission waits when the pool size is N.

### [H-ID-01] HIGH — case id `.` and `..` pass the allowlist

```191:195:app/cases.py
def get(cid: str) -> Case | None:
    if not re.fullmatch(r"[\w.-]+", cid):
        return None
    folder = CASES_DIR / cid
    return Case(folder) if (folder / "case.json").exists() else None
```

`..` matches. If the parent of `CASES_DIR` contains `case.json` (the legacy layout in `app/config.py:32-34` looks at that parent), `GET /api/cases/..` and `DELETE /api/cases/..` operate on that directory. The UI hash parser uses the same class (`web/app.js:1248`).

Fix (phase 3, small enough to do with the id check whenever tests land): reject ids that are `.` or `..` or that resolve outside `CASES_DIR`.

Effort: S. Verify: `get("..")` is `None` even if a parent `case.json` exists.

### [H-ESRI-01] HIGH — satellite basemap is keyless Esri World Imagery

```132:132:web/app.js
    tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"] });
```

No key, no attribution string of our own, not listed in a notice. Esri's World Imagery service is not a free commercial tile CDN. Trigger: the user toggles قمر صناعي.

Fix: ship an allowed raster (or a keyed Esri style) and name it in `THIRD_PARTY.md`. Not the Google fix; do not pretend Esri is cleared because Google is gated.

Effort: M. Verify: the satellite toggle URL is one we have a written right to call.

### [H-NET-01] HIGH — "local" UI depends on Google Fonts and Carto

`web/index.html:9-10` preconnects to `fonts.googleapis.com` and loads Inter and IBM Plex Sans Arabic from `fonts.googleapis.com`. The map style is `https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json` (`web/app.js:112`). Offline, the map errors and the type falls back. Every visit also contacts Google.

Fix (phase 5 / packaging): vendor the two families and a style JSON. Effort: M.

### [H-RANK-01] HIGH — the default model is labelled "the best" against the table in the same file

```16:19:app/openrouter.py
    {"id": "anthropic/claude-opus-5.5", "label": "Claude Opus 5.5", "tag": "الأفضل",
     "note": "الأول بالاختبار · وسيط الخطأ 10.9 كم · الدولة صح 86%"},
    {"id": "anthropic/claude-fable-5.1", "label": "Claude Fable 5.1", "tag": "",
     "note": "متعادل مع الأول · 8.7 كم · سعره ضعفين ونص"},
```

README repeats 10.9 km as 1st and 8.7 km as tied 1st, and says `google/gemini-4-argon` was not benchmarked (README lines 27-35). `OR_DEFAULT` is opus (`app/config.py:52`). I did not re-run GeoGuessBench. A lower median on the same table is already enough to drop the "الأفضل" tag until a re-rank exists.

Fix (phase 2): re-measure and rank from that run. Effort: L.

## MEDIUM

### [M-LOCK-01] MEDIUM — one lock for every case, and the model catalog holds it across the network

`_lock` in `app/cases.py:25` wraps every `update`, `emit`, and `events` read. `catalog()` in `app/openrouter.py:38-44` holds `_lock` during `requests.get` (timeout 30s). Trigger: a settings save while a case is writing, or a slow OpenRouter model list.

Fix: per-case locks; do not hold the catalog lock during I/O. Effort: S. Phase 3.

### [M-IMPORT-01] MEDIUM — importing the package creates directories and rewrites cases

`CASES_DIR.mkdir` runs at import (`app/config.py:38-39`). `cases.recover_stale()` runs at import of the server (`app/server.py:46`) and flips every `queued` / `recon` / `analysing` case to `error`. Trigger: `import app.server` in a test, or a second process started while a run is live.

Fix: create the directory in `main()`, recover only from the process that owns the port. Effort: S. Phase 4 tests will trip this immediately.

### [M-TEST-01] MEDIUM — no tests, no ruff config, no CI

No `tests/`, no `pyproject.toml`, no workflow. `pytest` and `ruff` are not installed here. Phase definition of done cannot be met until they exist. Effort: M. Phase 4, with the minimum runner added as soon as phase 1 needs a green `pytest`.

### [M-PKG-01] MEDIUM — Windows-only bootstrap

`setup.bat` and `run.bat` are the only entrypoints. `setup.bat:6-9` assumes `uv`, Python 3.12, and a CUDA wheel URL. A Linux or macOS clone has no command. Effort: M. Phase 4.

### [M-GEOINT-01] MEDIUM — a fresh clone cannot geolocate

`GEOINT` defaults to `~/.claude/skills/geoint` (`app/config.py:41-42`). `run_script` returns rc 127 if the script is missing (`app/tools.py:51-52`). The status endpoint reports `geoint_ok` (`app/server.py:72`) and nothing installs the skill. Effort: L. Phase 4.

### [M-PRUNE-01] MEDIUM — context control is "keep 6 images" and a 20k-character cut

`_prune_images(..., keep=6)` (`app/agent.py:183-194`). Recon is sliced `recon_md[:20000]` (`app/agent.py:349`) and person/plate recon `[:12000]` (`app/identify.py:302`, `app/identify.py:325`). Trigger: a sweep that returns several sheets, then later turns forget them. Effort: M. Phase 3.

### [M-REV-01] MEDIUM — reverse image search defaults on

`rev: bool = Form(True)` (`app/server.py:193`). The checkbox is `checked` (`web/index.html:202`) and `store.get("rev", true)` (`web/app.js:1179`). The label does say the photo is sent to Yandex and Baidu. Trigger: Find Region with the default form. Effort: S. Phase 5 wants the disclosure kept; the default should be off for a commercial build.

### [M-BING-01] MEDIUM — Apple, Bing, and Yandex panoramas are still one argument away

Tool text lists `google, apple, bing, yandex, mapillary, kartaview, panoramax` (`app/agent.py:89`). Only Google is called out in the README. The other three closed platforms have the same class of terms problem. Effort: S. Gate them the same way as Google when the Google gate lands, or drop them from the tool description.

### [M-CAT-01] MEDIUM — OpenRouter model list failure mode is an exception on the request thread

`catalog()` calls `raise_for_status()` with no stale cache (`app/openrouter.py:40-43`). Settings and `/api/models` turn that into HTTP 502 (`app/server.py:142-143`, `app/server.py:157-160`). The agent calls `OR.reasoning` → `catalog()` inside a run (`app/openrouter.py:101-104`). Trigger: OpenRouter down mid-run. The run dies instead of skipping the reasoning parameter. Effort: S. Phase 3.

## LOW

### [L-PHOTO-01] LOW — `Case.photo` indexes an empty glob

`app/cases.py:70-72` returns `files[0]` with no empty check. Trigger: `original/` deleted by hand, then rerun (`app/server.py:219` calls `old.photo.read_bytes()`). Effort: S.

### [L-REPORT-FONT] LOW — the HTML report names a font it does not load

`app/report.py:155` sets `IBM Plex Sans Arabic` but the report document has no stylesheet link. The UI page loads the font from Google; the report does not. Effort: S.

### [L-CSP-01] LOW — CSP is only `frame-ancestors 'none'`

`app/server.py:42`. Scripts are same-origin, so this is defence-in-depth, not a hole by itself. Effort: S.

### [L-UTC-01] LOW — the clock is UTC

`web/app.js:1238`. The label says UTC, so this is a product choice, not a bug. Left here so nobody "fixes" it into local time without deciding.

## What this pass did not do

- Did not run `uv run python -m app.server` (no uv, no venv, no geoint).
- Did not read `web/vendor/maplibre-gl.js` or `mapbox-gl-rtl-text.js` past the licence headers. MapLibre header says 3-Clause BSD, `v4.7.1`. rtl-text file is the BSD-2 notice plus ICU.
- Did not execute GeoGuessBench, and did not open the geoint `recon.py` / `gsv.py` / `pano.py` sources (not on disk, not in this repo).
- Did not change code. Phase 0 is the two markdown files only.
