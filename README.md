# SAQR · صقر — local visual geolocation

Upload a photo, watch it get analysed live, and get a pin with a confidence radius and visual proof.
The app, the case files and the local models run on this computer. What goes out: the AI reasoning step (if a key
is set), the map / Street View / satellite / search services the tools query, and the reverse image search (see below).

## Requirements

- Windows, Python 3.12 via [uv](https://docs.astral.sh/uv/) (`winget install astral-sh.uv`)
- The **geoint** skill at `%USERPROFILE%\.claude\skills\geoint` (or set `SAQR_GEOINT`); recon, Street View,
  satellite and terrain tools come from it. The status bar says when it is missing.
- An NVIDIA GPU is optional (MegaLoc / GeoCLIP run on the CPU too, slower). The first run downloads the models.

## Run

1. Once: `setup.bat` (creates `.venv`, installs `requirements.txt`, CUDA torch with a CPU fallback, copies `.env.example`).
2. `run.bat` → opens http://127.0.0.1:8765 when the server answers (`SAQR_PORT` changes the port).
3. Optional but recommended: Settings (⚙) → **OpenRouter** (one key, any lab's model) or **Anthropic** (Claude direct).
   SAQR checks the key and writes it to `saqr\.env` (`OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY`, `SAQR_OR_MODEL`,
   `SAQR_PROVIDER`). `.env.example` lists every setting.

## Models (OpenRouter)

The picker lists these, ranked by GeoGuessBench v2 (2026-10-06, 210 street photos, one guess each, medium effort),
with live prices from OpenRouter. Any other model that takes images and supports tools can be typed in.

| Model | Benchmark | Median error | Country right |
|---|---|---|---|
| `anthropic/claude-opus-5.5` (default) | 1st | 10.9 km | 86% |
| `anthropic/claude-fable-5.1` | tied 1st | 8.7 km | 87% |
| `meta/muse-glimmer-30b` | 3rd, cheapest | 49.9 km | 78% |
| `openai/gpt-6-astra` | 4th | 21.6 km | 77% |
| `openai/gpt-6.1-sol` | 5th | 37.8 km | 75% |
| `z-ai/glm-5.3-flash` | 6th | 61.7 km | 75% |
| `google/gemini-4-argon` | not benchmarked yet | | |

The benchmark measures the eye, not tool use; SAQR's prompts were tuned on Claude, so other models may call the
tools less well. Web search on OpenRouter uses its `openrouter:web_search` server tool (billed by OpenRouter).

Without a key SAQR runs on local metadata, OCR, object detection, and a GeoCLIP world prior (MIT).
StreetCLIP (CC-BY-NC-4.0) is not part of that path. `recon.py` is called with `--skip calib,prior`,
then `prior.py --models geoclip` writes `work/recon/prior`. `SAQR_ALLOW_NC_MODELS=1` on a private,
non-commercial install runs StreetCLIP and GeoCLIP together inside recon and does not add that
follow-up call. Reverse image search is a separate switch, described below. It is not the prior.
The StreetCLIP-versus-GeoCLIP gap has not been scored on a SAQR corpus (H-GEOCLIP-01). A local
country guess is a starting area, not a measured accuracy.

## Modules

| Module | What it does |
|---|---|
| تحديد المنطقة (Find Region) | Quick pass: country / region / city with an honest radius. Private homes and private people stop at city level in this mode. |
| تحديد الشارع (Find Street) | Deep pass: street-level sweeps (MegaLoc), terrain skyline matching, satellite evidence. Same city-level stop for a private home. |
| تحديد مكان خاص (Private place) | Separate prompt. It does not stop at the city. It can search listings (Airbnb, aqar.fm, Bayut, Haraj) and pin a building when a listing or a text anchor matches the photo. It may read and search a plate number as an extra anchor. |
| من هذا الشخص؟ (Who is this?) | Photo and/or an email, a phone number, or a name. Web search and Gravatar. Files a name, a role, and accounts when the search results support them. Needs an API key. |
| لوحة السيارة (Plate) | Reads the plate characters, names the vehicle, and searches that plate text. An owner name is filed only when a page shows one. Needs an API key. |
| التحقق من الصورة (Verify Image) | Metadata + error level analysis + an AI reading of manipulation / AI-generation signals |
| تحديد السيارة (Identify Car) | Make, model, year range from exterior or interior. This module's prompt does not read the plate. Needs an API key. |
| القضايا (Cases) | Every case on one map; click to reopen, replay its live log, stop or re-run it |

In a case: **stop** ends a run after the current step, **re-run** starts a new case from the same photo with another
module (or with/without reverse search), and the **notes** tab keeps your own notes, which go into the report.
Pins, measure lines and notes on the map board are saved in `saqr_board.json`; a damaged board file is set aside
instead of being overwritten.

## Reverse image search

"بحث عكسي" defaults to on for Find Region, Find Street, Private place, and Plate. It uploads the photo to Yandex and Baidu to look for other copies of it. Untick it before a run, or in the re-run menu, when the photo must not leave this computer.

## Case files

Each case is a folder `<date>_saqr-<name>-<id>\` with `report.md` (also served as HTML from the case view),
`evidence\`, `original\`, `events.jsonl` (the live log), `notes.md`, `truth.json` when an analyst confirms a pin, and `work\` (raw tool output).
A confirmation is ground truth for that case. A dismissal marks the pin and does not replace a truth already saved.
Cases go to `saqr\cases\`, or to `SAQR_CASES` if set; an install that already keeps cases in the folder above
`saqr` keeps using it. Deleted cases go to `_saqr_trash\` in the same place. None of this is committed to git.

## How it works

`app/agent.py` runs the geoint skill's recon, puts the model guess on the map, then gives the AI model
(Claude direct: `claude-opus-5-5`, adaptive thinking; or any OpenRouter model via `app/openrouter.py`) these tools:
`view_photo`, `web_search`, `geocode`, `osm_query`, `listing_search`, `streetview_near`, `streetview_views`, `streetview_sweep`,
`satellite`, `terrain_view`, `pin_candidate`, `final_answer`. Person and plate modes use a separate loop: `view_photo`,
`web_lookup`, `gravatar_lookup` (person only), and a single file call. Every image a tool makes is shown to the model and
filed as evidence. The browser follows the run over server-sent events and picks up where it left off after a
reconnect. The server only answers on 127.0.0.1 and rejects requests from other sites.

The interface is a dark frosted-glass layout over MapLibre GL (vendored in `web/vendor/`, BSD-3, with the
mapbox-gl-rtl-text plugin, BSD-2, so Arabic map labels are joined and ordered right to left; Arabic place names are
shown where OpenStreetMap has them). It is Arabic right-to-left and also works on a phone.

## Limits (by design)

- Exact points still need an anchor (text, landmark, distinctive skyline, a covered road). A city can be named
  from one strong cluster of clues. Generic landscapes stay at region level with a wide radius instead of an invented point.
  Lookalike Gulf cities are compared explicitly; the tool must not default to Dubai.
- Find Region and Find Street stop at city level when the photo is a private person or a private home, and they do not pin the building. Private-place mode does not keep that stop.
- Person search from a photo, an email, a phone number, or a name is built. So is listing search, and so is reading a plate number in the plate module and in private-place mode. The car module does not read the plate. Find Region / Find Street treat a plate only by style, colours, and country or region code.
- Street-level search defaults to Mapillary. Kartaview and Panoramax are the other open providers.
  Google Street View, Google satellite tiles, and Apple, Bing, and Yandex panoramas stay off until their own
  key is set: `SAQR_GOOGLE_KEY` or `GOOGLE_MAPS_API_KEY`, `SAQR_APPLE_KEY`, `SAQR_BING_KEY`, `SAQR_YANDEX_KEY`.
  A Google key does not unlock the others. Esri imagery in the satellite toggle is a separate, still-open question.
- Each AI analysis costs API credit; Find Street costs more than Find Region.

## Licence

SAQR's own code is proprietary. See `LICENSE`, `NOTICE`, and `THIRD_PARTY.md`.
MapLibre GL JS (BSD-3-Clause) and mapbox-gl-rtl-text (BSD-2-Clause, plus the ICU notice) are vendored in `web/vendor/`.
The GeoInt scripts are MIT and are not in this repository. A commercial run calls GeoInt `prior.py --models geoclip` only.
StreetCLIP weights are not included; they are CC-BY-NC-4.0 and load only when `SAQR_ALLOW_NC_MODELS=1`.
