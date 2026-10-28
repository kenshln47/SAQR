"""SAQR local server: upload a photo, watch the analysis stream in, keep every case on disk."""
from __future__ import annotations

import asyncio
import json
import math
import shutil
import os
import re
import threading
import time

import requests
from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import cases
from . import openrouter as OR
from .config import (CASES_DIR, GEOINT, OR_DEFAULT, ROOT, SCRIPTS, UV, WEB_DIR, engine_label, load_dotenv,
                     model_name, provider)

load_dotenv()
app = FastAPI(title="SAQR")
# DNS rebinding: a website that re-points its name to 127.0.0.1 still sends its own Host header, so refuse it
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
MODES = {"region", "street", "private", "verify", "car", "person", "plate"}
MAX_UPLOAD = 40 * 1024 * 1024
BOARD = CASES_DIR / "saqr_board.json"
PIN_KINDS = {"place", "camera", "note"}


@app.middleware("http")
async def no_stale_ui(request: Request, call_next):
    resp = await call_next(request)
    if not request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-cache"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    return resp


cases.recover_stale()   # nothing can still be running when the server starts


def _start(case: cases.Case, mode: str) -> None:
    from .agent import run_geolocate
    from .analysis import run_car, run_verify
    from .identify import run_person, run_plate
    target = {"region": lambda: run_geolocate(case, "region"), "street": lambda: run_geolocate(case, "street"),
              "private": lambda: run_geolocate(case, "private"), "verify": lambda: run_verify(case),
              "car": lambda: run_car(case), "person": lambda: run_person(case), "plate": lambda: run_plate(case)}[mode]
    threading.Thread(target=target, daemon=True, name=f"case-{case.id}").start()


def _hint(name: str) -> str:
    key = os.environ.get(name, "")
    return f"…{key[-4:]}" if len(key) > 12 else ""


@app.get("/api/status")
def status():
    prov = provider()
    return {"ready": bool(prov), "claude": bool(prov), "provider": prov, "model": model_name() if prov else "",
            "label": engine_label() if prov else "",
            "key_hint": _hint("OPENROUTER_API_KEY" if prov == "openrouter" else "ANTHROPIC_API_KEY") if prov else "",
            "keys": {"anthropic": _hint("ANTHROPIC_API_KEY"), "openrouter": _hint("OPENROUTER_API_KEY")},
            "or_model": os.environ.get("SAQR_OR_MODEL") or OR_DEFAULT, "cases_dir": str(CASES_DIR),
            "geoint_ok": (SCRIPTS / "recon.py").exists(), "geoint_path": str(GEOINT), "uv_ok": bool(shutil.which(UV))}


def _local_origin(request: Request) -> None:
    """Only SAQR's own page may change anything: blocks other websites from posting to 127.0.0.1."""
    origin = request.headers.get("origin", "")
    if origin and not re.match(r"^http://(127\.0\.0\.1|localhost)(:\d+)?$", origin):
        raise HTTPException(403, "only SAQR itself can do this")
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "only SAQR itself can do this")


def _write_env(updates: dict[str, str]) -> None:
    """Set (or, with an empty value, remove) KEY=VALUE lines in saqr/.env and in this process."""
    env = ROOT / ".env"
    lines = env.read_text(encoding="utf-8").splitlines() if env.exists() else []
    lines = [l for l in lines if l.split("=", 1)[0].strip() not in updates]
    lines = [f"{k}={v}" for k, v in updates.items() if v] + lines
    env.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for k, v in updates.items():
        if v:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)


def _check_anthropic(key: str) -> None:
    if not key.startswith("sk-ant-") or len(key) < 30 or any(c.isspace() for c in key):
        raise HTTPException(400, "مفتاح Anthropic لازم يبدأ بـ sk-ant- (انسخه كامل من console.anthropic.com)")
    import anthropic
    try:
        anthropic.Anthropic(api_key=key, max_retries=0, timeout=20).models.list(limit=1)
    except anthropic.AuthenticationError:
        raise HTTPException(400, "Anthropic رفض المفتاح: تأكد إنك نسخته صح وإنه مو ملغي")
    except anthropic.APIConnectionError:
        raise HTTPException(502, "ما قدرت أوصل لـ Anthropic: تأكد من الإنترنت")
    except anthropic.APIStatusError as e:
        raise HTTPException(400, f"Anthropic رد بخطأ {e.status_code}: {e.message}")


def _check_openrouter(key: str) -> None:
    if not key.startswith("sk-or-") or len(key) < 30 or any(c.isspace() for c in key):
        raise HTTPException(400, "مفتاح OpenRouter لازم يبدأ بـ sk-or- (انسخه كامل من openrouter.ai/keys)")
    try:
        OR.check_key(key)
    except PermissionError as e:
        raise HTTPException(400, str(e))
    except requests.RequestException:
        raise HTTPException(502, "ما قدرت أوصل لـ OpenRouter: تأكد من الإنترنت")


@app.post("/api/settings/ai")
def set_ai(request: Request, body: dict = Body(...)):
    """{provider, key?, model?, remove?}: save a key and/or the OpenRouter model, and make that provider active."""
    _local_origin(request)
    prov = body.get("provider")
    if prov not in ("anthropic", "openrouter"):
        raise HTTPException(400, "unknown provider")
    env_key = "OPENROUTER_API_KEY" if prov == "openrouter" else "ANTHROPIC_API_KEY"
    if body.get("remove"):
        _write_env({env_key: "", **({"SAQR_PROVIDER": ""} if os.environ.get("SAQR_PROVIDER") == prov else {})})
        return status()
    key = str(body.get("key", "")).strip()
    if not key and not os.environ.get(env_key):
        raise HTTPException(400, "الصق المفتاح أول")
    updates = {"SAQR_PROVIDER": prov}
    if prov == "openrouter":
        model = str(body.get("model") or os.environ.get("SAQR_OR_MODEL") or OR_DEFAULT).strip()
        try:
            bad = OR.usable(model)
        except requests.RequestException:
            raise HTTPException(502, "ما قدرت أجيب قائمة نماذج OpenRouter: تأكد من الإنترنت")
        if bad:
            raise HTTPException(400, bad)
        updates["SAQR_OR_MODEL"] = model
    if key:
        (_check_openrouter if prov == "openrouter" else _check_anthropic)(key)
        updates[env_key] = key
    _write_env(updates)
    return status()


@app.get("/api/models")
def models():
    """Recommended OpenRouter models with live prices, plus every model that can run SAQR (images + tools)."""
    try:
        cat = OR.catalog()
    except requests.RequestException:
        raise HTTPException(502, "ما قدرت أجيب قائمة نماذج OpenRouter: تأكد من الإنترنت")
    rec = [{**r, "available": r["id"] in cat and OR.fits(cat[r["id"]]),
            **({"price": OR.price(cat[r["id"]])} if r["id"] in cat else {})} for r in OR.RECOMMENDED]
    usable = sorted((m for m in cat.values() if OR.fits(m) and ":" not in m["id"]), key=lambda m: -m.get("created", 0))
    return {"recommended": rec, "all": [{"id": m["id"], "name": m.get("name", m["id"])} for m in usable],
            "source": "GeoGuessBench v2 · 2026-10-06 · 210 صورة شارع"}


async def _read_limited(photo: UploadFile) -> bytes:
    """Read the upload in chunks and stop at the limit instead of loading any size into memory."""
    buf = bytearray()
    while chunk := await photo.read(1 << 20):
        buf += chunk
        if len(buf) > MAX_UPLOAD:
            raise HTTPException(413, "الصورة أكبر من 40 MB")
    if not buf:
        raise HTTPException(400, "الملف فاضي")
    return bytes(buf)


def _new(name: str, data: bytes, mode: str, **extra) -> dict:
    if mode not in MODES:
        raise HTTPException(400, "unknown mode")
    try:
        case = cases.create(name, data, mode, **extra)
    except cases.NotAnImage as e:
        raise HTTPException(400, str(e))
    _start(case, mode)
    return case.load()


@app.post("/api/cases")
async def new_case(request: Request, photo: UploadFile | None = File(None), mode: str = Form("region"),
                   rev: bool = Form(True), query: str = Form("")):
    _local_origin(request)
    if mode not in MODES:
        raise HTTPException(400, "unknown mode")
    q = query.strip()[:200]
    data = await _read_limited(photo) if (photo is not None and photo.filename) else b""
    if not data and not (mode == "person" and q):
        raise HTTPException(400, "ارفع صورة، أو اكتب إيميل أو جوال أو اسم")
    return _new((photo.filename if data else q) or "photo.jpg", data, mode,
                rev=bool(rev), query=q, text_only=not data)


def _case(cid: str) -> cases.Case:
    case = cases.get(cid)
    if not case:
        raise HTTPException(404, "القضية مو موجودة")
    return case


@app.post("/api/cases/{cid}/rerun")
def rerun_case(cid: str, request: Request, body: dict = Body(default={})):
    """Same photo, new case: another mode, or the model now chosen in Settings."""
    _local_origin(request)
    old = _case(cid)
    d = old.load()
    mode = body.get("mode") or d.get("mode", "region")
    return _new(d.get("filename") or old.photo.name, old.photo.read_bytes(), mode,
                rev=bool(body.get("rev", d.get("rev", True))), rerun_of=old.id,
                query=d.get("query", ""), text_only=bool(d.get("text_only")))


@app.post("/api/cases/{cid}/cancel")
def cancel_case(cid: str, request: Request):
    """Ask a running analysis to stop; it stops after the step it is in (a Street View sweep can take minutes)."""
    _local_origin(request)
    case = _case(cid)
    if not case.running():
        raise HTTPException(409, "التحليل مو شغال")
    case.update(cancel=True)
    case.emit("log", text="طلبت الإيقاف: بيوقف بعد الخطوة الحالية")
    return case.load()


@app.get("/api/cases")
def list_cases():
    return cases.all_cases()


@app.get("/api/cases/{cid}")
def get_case(cid: str):
    case = _case(cid)
    return {**case.load(), "events": case.events(), "has_report": (case.dir / "report.md").exists()}


@app.get("/api/cases/{cid}/stream")
async def stream(cid: str, request: Request):
    """Server-sent events. Each event carries its index as id, so a reconnect resumes instead of replaying."""
    case = _case(cid)
    try:
        start = int(request.headers.get("last-event-id") or request.query_params.get("from") or 0)
    except ValueError:
        start = 0
    if request.headers.get("last-event-id"):
        start += 1

    async def gen():
        sent = max(0, start)
        idle = 0
        yield "retry: 2000\n\n"
        while True:
            if await request.is_disconnected():
                return
            evs = case.events(sent)
            for i, ev in enumerate(evs):
                yield f"id: {sent + i}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
            sent += len(evs)
            if not case.running() and not evs:
                idle += 1
                if idle > 2:
                    yield "event: end\ndata: {}\n\n"
                    return
            await asyncio.sleep(0.6)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.get("/api/cases/{cid}/file/{path:path}")
def case_file(cid: str, path: str):
    case = _case(cid)
    full = (case.dir / path).resolve()
    if case.dir.resolve() not in full.parents or not full.is_file():
        raise HTTPException(404)
    return FileResponse(full)


@app.get("/api/cases/{cid}/photo")
def case_photo(cid: str):
    return FileResponse(_case(cid).preview)


@app.get("/api/cases/{cid}/notes")
def get_case_notes(cid: str):
    p = _case(cid).dir / "notes.md"
    return {"notes": p.read_text(encoding="utf-8") if p.exists() else ""}


@app.put("/api/cases/{cid}/notes")
def put_case_notes(cid: str, request: Request, body: dict = Body(...)):
    """The analyst's own notes for one case; they go into its report."""
    _local_origin(request)
    case = _case(cid)
    notes = str(body.get("notes", ""))[:20000]
    tmp = case.dir / "notes.tmp"
    tmp.write_text(notes, encoding="utf-8")
    os.replace(tmp, case.dir / "notes.md")
    if not case.running():   # a running analysis writes the report itself when it ends
        from .report import write_report
        write_report(case)
    return {"ok": True, "length": len(notes)}


@app.get("/api/cases/{cid}/report")
def case_report(cid: str):
    """report.md rendered as a page, with its evidence images."""
    from fastapi.responses import HTMLResponse
    from .report import render_html
    case = _case(cid)
    md = case.dir / "report.md"
    if not md.exists():
        raise HTTPException(404, "التقرير ما انكتب بعد")
    return HTMLResponse(render_html(case.id, md.read_text(encoding="utf-8")))


TRASH = CASES_DIR / "_saqr_trash"


@app.delete("/api/cases/{cid}")
def delete_case(cid: str, request: Request):
    """Move the case folder to <cases dir>\\_saqr_trash (recoverable), never a hard delete."""
    _local_origin(request)
    case = _case(cid)
    if case.running():
        raise HTTPException(409, "التحليل لسا شغال: أوقفه أول وبعدين احذفه")
    TRASH.mkdir(exist_ok=True)
    dest = TRASH / case.id
    if dest.exists():
        dest = TRASH / f"{case.id}-{os.getpid()}-{len(list(TRASH.iterdir()))}"
    shutil.move(str(case.dir), str(dest))
    return {"ok": True, "moved_to": str(dest)}


@app.get("/api/board")
def get_board():
    if not BOARD.exists():
        return {"pins": [], "notes": ""}
    try:
        raw = BOARD.read_text(encoding="utf-8")
    except OSError:   # locked or unreadable: refuse, so the page never saves an empty board over it
        raise HTTPException(503, "ما قدرت أقرا ملف اللوحة")
    try:
        b = json.loads(raw)
        for pin in b.get("pins", []):
            if not (math.isfinite(float(pin["lat"])) and math.isfinite(float(pin["lon"]))):
                raise ValueError
        return {"pins": b.get("pins", []), "notes": str(b.get("notes", ""))}
    except (ValueError, KeyError, TypeError, AttributeError):
        bad = BOARD.with_name(f"saqr_board.corrupt-{int(time.time())}.json")
        os.replace(BOARD, bad)   # keep the broken file for the user, start a clean board
        return {"pins": [], "notes": "", "recovered": str(bad)}


@app.put("/api/board")
def put_board(request: Request, board: dict = Body(...)):
    _local_origin(request)
    pins = []
    for p in board.get("pins", [])[:500]:
        try:
            lat, lon = float(p["lat"]), float(p["lon"])
            if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90):
                raise ValueError
            lon = ((lon + 180) % 360) - 180
            pins.append({"id": str(p["id"])[:40], "lat": lat, "lon": lon,
                         "label": str(p.get("label", ""))[:120], "created": str(p.get("created", ""))[:40],
                         "kind": p.get("kind") if p.get("kind") in PIN_KINDS else "place"})
        except (KeyError, TypeError, ValueError):
            raise HTTPException(400, "bad pin")
    clean = {"pins": pins, "notes": str(board.get("notes", ""))[:20000]}
    tmp = BOARD.with_suffix(".tmp")
    tmp.write_text(json.dumps(clean, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, BOARD)
    return clean


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")


def main() -> None:
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("SAQR_PORT") or 8765), log_level="warning")


if __name__ == "__main__":
    main()
