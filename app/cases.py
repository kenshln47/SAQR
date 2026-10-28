"""Case folders on disk: <cases dir>\\<date>_saqr-<id>\\ with case.json, events.jsonl, original/, evidence/, report.md."""
from __future__ import annotations

import io
import json
import math
import os
import re
import shutil
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps

from .benchscore import haversine_km
from .config import CASES_DIR

try:   # iPhone photos: lets PIL (and so every analysis path) open HEIC/HEIF
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

_lock = threading.Lock()
RUNNING = ("queued", "recon", "analysing")
EXT = {"JPEG": ".jpg", "MPO": ".jpg", "PNG": ".png", "WEBP": ".webp", "GIF": ".gif", "BMP": ".bmp",
       "TIFF": ".tif", "HEIF": ".heic", "AVIF": ".avif"}
BROWSER_SAFE = {".jpg", ".png", ".webp", ".gif", ".bmp", ".avif"}


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_atomic(path: Path, text: str) -> None:
    """Readers never see a half-written case.json: write a temp file, then swap it in."""
    tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex[:6]}.tmp")
    tmp.write_text(text, encoding="utf-8")
    for attempt in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:   # Windows: a reader has the file open for a moment
            time.sleep(0.05)
    os.replace(tmp, path)


class Case:
    def __init__(self, folder: Path):
        self.dir = folder
        self.id = folder.name

    # ---- files
    @property
    def meta_path(self) -> Path:
        return self.dir / "case.json"

    @property
    def events_path(self) -> Path:
        return self.dir / "events.jsonl"

    @property
    def evidence(self) -> Path:
        p = self.dir / "evidence"
        p.mkdir(exist_ok=True)
        return p

    @property
    def photo(self) -> Path:
        files = sorted((self.dir / "original").glob("*"))
        return files[0]

    @property
    def preview(self) -> Path:
        """What the browser shows: a JPEG copy for formats browsers cannot decode (HEIC, TIFF)."""
        p = self.dir / "preview.jpg"
        return p if p.exists() else self.photo

    # ---- state
    def load(self) -> dict:
        for attempt in range(20):
            try:
                return json.loads(self.meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, PermissionError):
                time.sleep(0.05)
        return json.loads(self.meta_path.read_text(encoding="utf-8"))

    def _save(self, d: dict) -> None:
        d["updated"] = _now()
        _write_atomic(self.meta_path, json.dumps(d, ensure_ascii=False, indent=1))

    def update(self, **fields) -> dict:
        with _lock:
            d = self.load()
            d.update(fields)
            self._save(d)
            return d

    def emit(self, kind: str, **data) -> None:
        """Append one event; the UI streams events.jsonl over SSE."""
        ev = {"t": time.time(), "kind": kind, **data}
        with _lock:
            with self.events_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    def events(self, start: int = 0) -> list[dict]:
        if not self.events_path.exists():
            return []
        with _lock:
            lines = self.events_path.read_text(encoding="utf-8").splitlines()
        out = []
        for x in lines[start:]:
            try:
                out.append(json.loads(x))
            except json.JSONDecodeError:
                out.append({"t": 0, "kind": "log", "text": "(سطر تالف في السجل)"})
        return out

    def add_candidate(self, cand: dict) -> list[dict]:
        with _lock:
            d = self.load()
            cands = d.get("candidates", [])
            cand["n"] = len(cands) + 1
            cands.append(cand)
            d["candidates"] = cands
            self._save(d)
        self.emit("candidate", candidate=cand)
        return cands

    def review(self, verdict: str, n: int | None = None, lat: float | None = None,
               lon: float | None = None, country: str | None = None) -> dict:
        """Analyst confirm or dismiss. Confirm writes truth. Dismiss does not replace it."""
        if verdict not in {"confirmed", "dismissed"}:
            raise ValueError("verdict")
        with _lock:
            d = self.load()
            if n is not None:
                match = next((c for c in d.get("candidates") or [] if c.get("n") == n), None)
                if match is None:
                    raise KeyError("candidate")
                match["review"] = {"verdict": verdict, "at": _now()}
                if lat is None and lon is None:
                    lat, lon = match.get("lat"), match.get("lon")
            else:
                final = d.get("final")
                if not isinstance(final, dict) or not final:
                    raise KeyError("final")
                final["review"] = {"verdict": verdict, "at": _now()}
                d["final"] = final
                if lat is None and lon is None:
                    lat, lon = final.get("lat"), final.get("lon")
                if country is None:
                    country = final.get("country")
            if verdict == "confirmed":
                if lat is None or lon is None:
                    raise ValueError("coordinates")
                lat_f, lon_f = float(lat), float(lon)
                if not math.isfinite(lat_f) or not math.isfinite(lon_f):
                    raise ValueError("coordinates")
                if not -90 <= lat_f <= 90 or not -180 <= lon_f <= 180:
                    raise ValueError("coordinates")
                truth = {"lat": lat_f, "lon": lon_f, "source": "analyst", "verdict": verdict,
                         "candidate_n": n, "at": _now()}
                if country:
                    truth["country"] = country
                final = d.get("final") if isinstance(d.get("final"), dict) else None
                if final and final.get("lat") is not None and final.get("lon") is not None:
                    truth["error_km"] = round(haversine_km(float(final["lat"]), float(final["lon"]), lat_f, lon_f), 3)
                d["truth"] = truth
                _write_atomic(self.dir / "truth.json", json.dumps(truth, ensure_ascii=False, indent=1))
            self._save(d)
        self.emit("review", verdict=verdict, n=n)
        return d

    def add_evidence(self, src: Path, caption: str) -> str:
        """Copy an image into evidence/ and announce it; returns its case-relative path."""
        dst = self.evidence / f"{int(time.time() * 1000)}_{src.name}"
        shutil.copyfile(src, dst)
        rel = f"evidence/{dst.name}"
        self.emit("evidence", path=rel, caption=caption)
        return rel

    # ---- control
    def cancelled(self) -> bool:
        return bool(self.load().get("cancel"))

    def running(self) -> bool:
        return self.load().get("status") in RUNNING


class NotAnImage(ValueError):
    pass


def _blank_png(w: int = 720, h: int = 460) -> bytes:
    """Stand-in image for a text-only case (person search by email / phone / name)."""
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (13, 19, 27)).save(buf, "PNG")
    return buf.getvalue()


def create(upload_name: str, data: bytes, mode: str, **extra) -> Case:
    """New case from uploaded bytes. Only real images are kept, saved under the extension of their actual format."""
    if not data:
        data = _blank_png()
    try:
        im = Image.open(io.BytesIO(data))
        fmt = im.format
        im.verify()
    except Exception:
        raise NotAnImage("الملف مو صورة مدعومة (JPG · PNG · WEBP · HEIC)")
    ext = EXT.get(fmt or "")
    if not ext:
        raise NotAnImage(f"صيغة الصورة {fmt} مو مدعومة")
    stem = re.sub(r"[^a-z0-9]+", "-", Path(upload_name).stem.lower()).strip("-")[:24] or "photo"
    cid = f"{datetime.now():%Y-%m-%d}_saqr-{stem}-{uuid.uuid4().hex[:6]}"
    folder = CASES_DIR / cid
    (folder / "original").mkdir(parents=True)
    (folder / "original" / f"photo{ext}").write_bytes(data)   # untouched: EXIF and GPS stay for the metadata step
    if ext not in BROWSER_SAFE:
        try:
            pv = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
            pv.thumbnail((2048, 2048))
            pv.save(folder / "preview.jpg", "JPEG", quality=88)
        except Exception:
            pass
    case = Case(folder)
    _write_atomic(case.meta_path, json.dumps({
        "id": cid, "mode": mode, "status": "queued", "created": _now(), "updated": _now(),
        "filename": upload_name, "candidates": [], "final": None, **extra,
    }, ensure_ascii=False, indent=1))
    return case


def get(cid: str) -> Case | None:
    if not re.fullmatch(r"[\w.-]+", cid):
        return None
    folder = CASES_DIR / cid
    return Case(folder) if (folder / "case.json").exists() else None


def all_cases() -> list[dict]:
    out = []
    for p in CASES_DIR.glob("*_saqr-*/case.json"):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return sorted(out, key=lambda d: d.get("created", ""), reverse=True)


def recover_stale() -> int:
    """At server start nothing can still be running: mark cases cut off by a stop as failed, so they can be deleted."""
    n = 0
    for d in all_cases():
        if d.get("status") in RUNNING:
            c = get(d["id"])
            if c:
                c.update(status="error", error="انقطع التحليل لأن الخادم انقفل قبل ما يخلص")
                c.emit("error", text="انقطع التحليل لأن الخادم انقفل قبل ما يخلص. تقدر تعيده من زر إعادة التحليل.")
                n += 1
    return n
