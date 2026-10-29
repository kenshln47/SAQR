# SAQR · صقر — local visual geolocation

Upload a still photo. The case is a folder on this computer. The run can put a pin on a map with a radius and file the images the tools return.

What stays local: the app, the case files, metadata, error-level analysis, and the local prior when those scripts run. What leaves the machine: the AI call if a key is set, the map and search hosts the tools use, and reverse image search unless this browser stored it off. The map does not work offline.

This is not a measured accuracy claim. There is no scored SAQR photo corpus. Comparison with Graylark Raven's public pages is [GAP.md](GAP.md). That file does not add a SAQR error number.

## Requirements

- Windows, Linux, or macOS. Python 3.12 via [uv](https://docs.astral.sh/uv/) (`winget install astral-sh.uv` on Windows).
- The GeoInt skill (MIT) is cloned by setup into `~/.claude/skills/geoint` (`%USERPROFILE%\.claude\skills\geoint` on Windows), or into `SAQR_GEOINT` if that is set, when `scripts/recon.py` is not already there. It is not copied into this repository. The status bar says when it is missing.
- An NVIDIA GPU is optional. `setup.bat` tries a CUDA torch wheel and falls back to CPU torch. `scripts/setup.sh` installs CPU torch unless `nvidia-smi -L` succeeds, then the cu130 index. GeoCLIP and MegaLoc weights are not in this repo. GeoInt downloads them when those scripts run. StreetCLIP is not on the commercial path.

## Run

Windows:

1. Once: `setup.bat` (creates `.venv`, installs `requirements.txt`, installs torch as above, copies `.env.example`).
2. `run.bat` opens http://127.0.0.1:8765 when the server answers. `SAQR_PORT` changes the port.

Linux and macOS:

1. Once: `scripts/setup.sh`.
2. `scripts/run.sh` → http://127.0.0.1:8765. `SAQR_PORT` changes the port.

Docker is optional. The process inside the container still binds `127.0.0.1`. On Linux, `docker run --network host` is how that port is the host's loopback. The image is not told to listen on `0.0.0.0`.

Then Settings (⚙) → **OpenRouter** (one key) or **Anthropic** (Claude direct). SAQR checks the key and writes `saqr\.env` (`OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY`, `SAQR_OR_MODEL`, `SAQR_PROVIDER`). `.env.example` lists the settings.

## Models

`OR_DEFAULT` is `anthropic/claude-opus-5.5` (`app/config.py`). Settings shows `RECOMMENDED` from `app/openrouter.py`, plus a price per million tokens when the OpenRouter catalog returns one. The comment above that list says the order is GeoGuessBench v2 (2026-10-06, 210 street photos, one guess, medium effort) and that the bench measures the eye, not tool use. SAQR did not run that bench. `H-RANK-01` is open. The default was not changed.

The list's own notes do not agree. The default row is tagged `الأفضل` and its note says الأول, median 10.9 km, country 86%. The next row, `anthropic/claude-fable-5.1`, has an empty tag and a note that puts it level with that row at 8.7 km. 8.7 is a smaller median than 10.9, so those two notes are not one ranking, and this README does not pick a winner from them. The rest of the notes, as written in that file: `meta/muse-glimmer-30b` الثالث, 49.9 km, 78%; `openai/gpt-6-astra` الرابع, 21.6 km, 77%; `openai/gpt-6.1-sol` الخامس, 37.8 km, 75%; `z-ai/glm-5.3-flash` السادس, 61.7 km, 75%; `google/gemini-4-argon` not measured by that bench. None of these figures is a SAQR result.

Web search on OpenRouter uses its `openrouter:web_search` server tool when the model call includes it.

Without a key, region and street runs use local metadata, OCR, object detection, and a GeoCLIP world prior (MIT). `recon.py` is called with `--skip calib,prior`, then `prior.py --models geoclip` writes `work/recon/prior`. `SAQR_ALLOW_NC_MODELS=1` (also `true` / `yes` / `on`) on a private, non-commercial install runs StreetCLIP and GeoCLIP together inside recon and does not add that follow-up. The StreetCLIP-versus-GeoCLIP gap has not been scored (`H-GEOCLIP-01`). A local country guess is a starting area, not a measured accuracy. Reverse image search is a separate switch. It is not the prior.

## What the modes actually do

Find Region and Find Street use `SYSTEM` in `app/agent.py`. That text tells the model not to geolocate a private person's home, school, or routine, to stop at city level, and never to read a plate number.

Private-place mode stops at the city. `PRIVATE_NOTE` stands alone and says so. The filed answer is forced to level `city` with a radius of at least 15 km (`app/limits.py`). Listing search is refused in this mode. A building, a school, and a routine are not pinned. A plate may be read as a location anchor. The prompt says not to name an owner. `B-PRIV-01` is closed by this gate, not by a better search.

Person mode does not identify a person. It does not search the web, does not call Gravatar, and does not send the photo out. It files `found: false` and an empty name (`app/limits.py`).

Plate mode reads the plate characters and names the vehicle. The owner field is cleared in code. The prompt says not to search for an owner. It needs an API key.

The car module's prompt says not to read the plate. Find Region and Find Street tell the model a plate counts only by style, colours, and country or region code.

`B-PRIV-01` is closed. Private-place mode stops at the city in the prompt and again when the answer is filed. Person mode does not match a photo, email, phone, or name to a person. Plate mode still reads the characters and does not record an owner.

| Module | What the code does |
|---|---|
| تحديد المنطقة (Find Region) | Country / region / city and a radius. Private homes and private people stop at city level in this mode. |
| تحديد الشارع (Find Street) | MegaLoc sweeps, terrain skyline, satellite tool. Same city-level stop for a private home. |
| تحديد مكان خاص (Private place) | Stops at the city. Does not pin a building, a school, or a routine. Listing search is refused. |
| من هذا الشخص؟ (Who is this?) | Does not identify a person. `found` is false. No web search and no Gravatar. |
| لوحة السيارة (Plate) | Reads the characters and names the vehicle. The owner field is cleared. Needs an API key. |
| التحقق من الصورة (Verify Image) | Metadata and error-level analysis always. With a key, one model reading: an assessment, two likelihoods, and signals. No named-generator list and no separate face-swap score. Without a key the assessment is inconclusive and the local checks still run. |
| تحديد السيارة (Identify Car) | One make, model, year range, and body type. Not ten ranked candidates and not reference images. The prompt does not read the plate. Needs an API key. |
| القضايا (Cases) | Cases on one map. Confirm writes `truth.json`. Possible and dismissed mark the pin and do not write or replace a truth. |

In a case: **stop** ends a run after the current step, **re-run** starts a new case from the same photo when that photo is still there (if it is gone, the rerun is HTTP 409), and the **notes** tab is your text, which goes into the report. Pins, measure lines, and notes on the map board are saved in `saqr_board.json`. A damaged board file is set aside instead of being overwritten.

## Reverse image search

"بحث عكسي" defaults to on for a browser that has not stored a choice. The label says the photo goes to Yandex and Baidu, and to clear the box if the photo is sensitive. The checkbox is stored in this browser (`saqr.rev`). A stored off stays off. A case that stored `rev: false` stays off, including on re-run. A case that stored `rev: true` stays on.

## Case files

Each case is a folder `<date>_saqr-<name>-<id>\` with `report.md` (also served as HTML), `evidence\`, `original\`, `events.jsonl`, `notes.md`, `truth.json` only after an analyst confirms a pin, and `work\`. Cases go to `saqr\cases\`, or to `SAQR_CASES` if set. An install that already keeps cases in the folder above `saqr` keeps using it. Delete moves the folder to `_saqr_trash\` in that same place. It is a move, not a wipe. None of this is committed to git.

## Privacy, terms, retention

One user, on 127.0.0.1. No SAQR account. [Privacy](web/legal/privacy.html), [terms](web/legal/terms.html), and [retention](web/legal/retention.html) name the person refusal, plate reading, and the city stop. The help panel says the same thing.

## How it works

`app/agent.py` runs the GeoInt recon, puts the model guess on the map, then gives the model these tools: `view_photo`, `web_search`, `geocode`, `osm_query`, `listing_search`, `streetview_near`, `streetview_views`, `streetview_sweep`, `satellite`, `terrain_view`, `pin_candidate`, `final_answer`. Claude direct uses `claude-opus-5-5` with adaptive thinking. OpenRouter uses `app/openrouter.py`. Person and plate use a separate loop in `app/identify.py`: `view_photo`, `web_lookup`, `gravatar_lookup` (person only), and one file call. Images a tool writes are shown to the model and filed as evidence. The browser follows the run over server-sent events. The server only answers on 127.0.0.1 and rejects mutations from other origins. There is no CORS middleware.

At most `SAQR_WORKERS` analyses run at once (default 2, cap 8). A further upload waits. The case panel shows turns, tool calls, and token totals when the provider reports them. The running transcript is cut to `SAQR_CONTEXT_TOKENS` (default 24000). An image counts as 1600 in that estimate. Recon text in the first prompt is cut to `SAQR_RECON_TOKENS` (default 8000). The estimate is 2 characters per token, not the provider's tokenizer. The panel adds the provider's own usage when a response includes it.

The interface is a dark frosted-glass layout over MapLibre GL JS 4.7.1 (vendored in `web/vendor/`, BSD-3) and mapbox-gl-rtl-text (BSD-2, plus ICU) so Arabic map labels can be shaped. The style document is local (`web/vendor/ofm-dark.json`). Tiles, glyphs, and sprites are requested from `tiles.openfreemap.org` when the map is on screen. If that host fails or rate-limits, the map does not load and SAQR does not switch to another free tile host. The replacement is the operator's own tiles: either a paid vector-tile style or a self-hosted OpenMapTiles/Planetiler (or Protomaps) endpoint, written into that style file. See ADR-012. The rest of the app still runs. OpenFreeMap's own pages, fetched with the style, say commercial use is allowed, the service is as-is with no SLA, and offline downloads are capped. Attribution is drawn from their TileJSON (OpenFreeMap, OpenMapTiles, OpenStreetMap). The style's upstream design is the OpenMapTiles dark-matter style (BSD-3 code, CC-BY-4.0 design); the file in `web/vendor/` is the runtime JSON, not that source repo. A shaded Natural Earth raster in the style is public domain. Inter and IBM Plex Sans Arabic are vendored (`web/fonts/`, SIL OFL). The page does not request `fonts.googleapis.com`.

## Limits that are actually in the code

- A tight point still needs an anchor (readable text, a distinctive skyline, a covered road). The region/street prompt says a generic landscape stays wide, and lookalike Gulf cities are not to be defaulted to Dubai.
- Street-level search defaults to Mapillary. Google Street View, Google satellite tiles, and Apple, Bing, and Yandex panoramas each need their own key: `SAQR_GOOGLE_KEY` or `GOOGLE_MAPS_API_KEY`, `SAQR_APPLE_KEY`, `SAQR_BING_KEY`, `SAQR_YANDEX_KEY`. One Google key does not unlock the others. `streetview_near` and `streetview_views` call Google and refuse without that key.
- The قمر صناعي toggle is Esri World Imagery (`server.arcgisonline.com`, zoom 3–19). The map credits Esri, Maxar, Earthstar Geographics, and the GIS User Community. The agent `satellite` tool defaults to `esri` and clamps that source at zoom 19. Wayback is still refused. It was not restored. Google satellite still needs a Google key. Bing satellite needs `SAQR_BING_KEY`. A Google key does not unlock it.
- Verify does not name a generator and does not emit a separate face-swap score. Car is one vehicle object, not a ranked ten with reference photos. There is no video mode.
- Each AI analysis spends provider credit. Find Street is allowed more tool use than Find Region.

## Licence

SAQR's own code is proprietary. See `LICENSE`, `NOTICE`, and `THIRD_PARTY.md`. That blocks read-only redistribution of this tree unless a separate grant says otherwise. MapLibre GL JS (BSD-3-Clause) and mapbox-gl-rtl-text (BSD-2-Clause, plus the ICU notice) are vendored in `web/vendor/`. The GeoInt scripts are MIT and are not in this repository. A commercial run calls GeoInt `prior.py --models geoclip` only. StreetCLIP weights are not included. They are CC-BY-NC-4.0 and load only when `SAQR_ALLOW_NC_MODELS=1`.
