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

Without a key SAQR runs on local models only: metadata, OCR, object detection, the GeoCLIP/StreetCLIP world prior
and (if enabled) reverse image search. Free, but country/region level only.

## Modules

| Module | What it does |
|---|---|
| تحديد المنطقة (Find Region) | Quick pass: country / region / city with an honest radius |
| تحديد الشارع (Find Street) | Deep pass: Street View sweeps (MegaLoc on the GPU), terrain skyline matching, satellite evidence |
| التحقق من الصورة (Verify Image) | Metadata + error level analysis + an AI reading of manipulation / AI-generation signals |
| تحديد السيارة (Identify Car) | Make, model, year range from exterior or interior (plates are ignored; needs a key) |
| القضايا (Cases) | Every case on one map; click to reopen, replay its live log, stop or re-run it |

In a case: **stop** ends a run after the current step, **re-run** starts a new case from the same photo with another
module (or with/without reverse search), and the **notes** tab keeps your own notes, which go into the report.
Pins, measure lines and notes on the map board are saved in `saqr_board.json`; a damaged board file is set aside
instead of being overwritten.

## Reverse image search

"بحث عكسي" (on by default for Find Region / Find Street) uploads the photo to Yandex and Baidu to look for other
copies of it. Untick it before a run, or in the re-run menu, when the photo must not leave this computer.

## Case files

Each case is a folder `<date>_saqr-<name>-<id>\` with `report.md` (also served as HTML from the case view),
`evidence\`, `original\`, `events.jsonl` (the live log), `notes.md` and `work\` (raw tool output).
Cases go to `saqr\cases\`, or to `SAQR_CASES` if set; an install that already keeps cases in the folder above
`saqr` keeps using it. Deleted cases go to `_saqr_trash\` in the same place. None of this is committed to git.

## How it works

`app/agent.py` runs the geoint skill's recon, puts the model guess on the map, then gives the AI model
(Claude direct: `claude-opus-5-5`, adaptive thinking; or any OpenRouter model via `app/openrouter.py`) these tools:
`view_photo`, `web_search`, `geocode`, `osm_query`, `streetview_near`, `streetview_views`, `streetview_sweep`,
`satellite`, `terrain_view`, `pin_candidate`, `final_answer`. Every image a tool makes is shown to the model and
filed as evidence. The browser follows the run over server-sent events and picks up where it left off after a
reconnect. The server only answers on 127.0.0.1 and rejects requests from other sites.

The interface is a glass HUD over MapLibre GL (vendored in `web/vendor/`, BSD-3), with an Arabic right-to-left
layout that also works on a phone.

## Limits (by design)

- Exact points need something to anchor them (text, landmark, distinctive skyline, a covered road). Generic
  landscapes end at region level with a wide radius; SAQR says so instead of inventing a point.
- Not built: identity lookup from email/phone/name, matching home interiors to addresses, rental-listing matching.
  The agent stops at city level for photos centred on private people or private homes.
- Street View and Google tiles are fetched without an API key: fine for personal use, not for a public service.
- Each AI analysis costs API credit; Find Street costs more than Find Region.
