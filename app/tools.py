"""Local geolocation tools for the agent. Each tool wraps a geoint script and returns text plus optional images.

Every tool returns ToolOut(text, images): text goes back to the model, images are both shown to the model and filed
as case evidence so the UI can display them.
"""
from __future__ import annotations

import base64
import hashlib
import html
import io
import json
import math
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageOps

from .cases import Case   # importing cases registers the HEIC opener
from .config import SCRIPTS, SECRET_ENV, UV, VENV_PY
from .licensing import normalise_pano, pano_block_reason, recon_skip_arg, satellite_block_reason

SAT_SOURCE = re.compile(r"(esri|google|google-hybrid|bing|wayback:\d{4}(-\d{2}){0,2})")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SAQR/1.0 (+local)"


@dataclass
class ToolOut:
    text: str
    images: list[tuple[Path, str]] = field(default_factory=list)   # (file, caption)
    is_error: bool = False


def run_script(case: Case, script: str, args: list[str], *, use_uv: bool = False, timeout: int = 900) -> tuple[int, str]:
    work = case.dir / "work"
    work.mkdir(exist_ok=True)
    cmd = ([UV, "run", str(SCRIPTS / script)] if use_uv else [str(VENV_PY), str(SCRIPTS / script)]) + args
    env = {k: v for k, v in os.environ.items() if k not in SECRET_ENV}   # the geoint scripts never need the API keys
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", UV=UV)
    try:
        r = subprocess.run(cmd, cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, env=env)
        return r.returncode, (r.stdout + ("\n" + r.stderr if r.returncode else "")).strip()
    except subprocess.TimeoutExpired:
        return 124, f"{script} timed out after {timeout}s"
    except OSError as e:   # uv or the geoint skill missing: degrade like a failed script instead of failing the case
        return 127, f"{cmd[0]} not found or not runnable ({e}); install uv and the geoint skill (see README)"


def upright(path: Path) -> Image.Image:
    """The image as the camera meant it: EXIF rotation applied, so portrait phone photos are not sideways."""
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


def image_block(path: Path, max_side: int = 1568) -> dict:
    im = upright(path)
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                         "data": base64.standard_b64encode(buf.getvalue()).decode()}}


def _tail(s: str, n: int = 4000) -> str:
    return s if len(s) <= n else "…" + s[-n:]


def _ll(lat: float, lon: float) -> str:
    return f"{lat:.6f},{lon:.6f}"


# ---------------------------------------------------------------- tools

def recon(case: Case) -> ToolOut:
    """First local pass: metadata, OCR, reverse search, object crops, world prior."""
    args = [str(case.photo), "--out-dir", "recon", "--skip", recon_skip_arg()]
    if not case.load().get("rev", True):
        args.append("--no-rev")
    rc, out = run_script(case, "recon.py", args, use_uv=True, timeout=1800)
    md = case.dir / "work" / "recon" / "recon.md"
    text = md.read_text(encoding="utf-8") if md.exists() else f"recon failed (rc={rc}): {_tail(out)}"
    imgs = []
    sheet = case.dir / "work" / "recon" / "detect" / "detect_sheet.jpg"
    if sheet.exists():
        imgs.append((sheet, "Detected objects (signs, poles, plates, vehicles)"))
    pmap = case.dir / "work" / "recon" / "prior" / "prior_map.png"
    if pmap.exists():
        imgs.append((pmap, "World-prior heat map (model ranking, not proof)"))
    return ToolOut(text, imgs, is_error=not md.exists())


def prior_json(case: Case) -> dict | None:
    p = case.dir / "work" / "recon" / "prior" / "prior.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def view_photo(case: Case, box: list[int] | None = None) -> ToolOut:
    """Look at the original photo, or a crop of it (pixel box x0,y0,x1,y1) to read small details."""
    im = upright(case.photo)
    w, h = im.size
    if box:
        x0, y0, x1, y1 = [int(v) for v in box]
        im = im.crop((max(0, x0), max(0, y0), min(w, x1), min(h, y1)))
        scale = max(1, int(900 / max(1, max(im.size))))
        if scale > 1:
            im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
    out = case.dir / "work" / f"crop_{int(time.time() * 1000)}.jpg"
    out.parent.mkdir(exist_ok=True)
    im.save(out, quality=92)
    return ToolOut(f"photo size {w}x{h}px (crop boxes use these pixels)" + (f", crop {box}" if box else ""),
                   [(out, f"Crop {box}" if box else "Original photo")])


def photo_size(case: Case) -> tuple[int, int]:
    return upright(case.photo).size


def streetview_near(case: Case, lat: float, lon: float, radius_m: int = 200) -> ToolOut:
    blocked = pano_block_reason("google")
    if blocked:
        return ToolOut(blocked + " streetview_near is Google Street View.", is_error=True)
    rc, out = run_script(case, "gsv.py", ["near", _ll(lat, lon), "--radius", str(int(radius_m))], timeout=180)
    return ToolOut(_tail(out, 3000), is_error=rc != 0)


def streetview_views(case: Case, lat: float, lon: float, headings: list[float] | None = None,
                     pitch: float = 0, fov: float = 90, radius_m: int = 300) -> ToolOut:
    blocked = pano_block_reason("google")
    if blocked:
        return ToolOut(blocked + " streetview_views is Google Street View.", is_error=True)
    hs = ",".join(str(int(h)) for h in (headings or [0, 60, 120, 180, 240, 300]))
    name = f"sv_{lat:.4f}_{lon:.4f}_{int(time.time())}.jpg"
    rc, out = run_script(case, "gsv.py", ["sheet", "--at", _ll(lat, lon), "--headings", hs, "--pitch", str(pitch),
                                          "--fov", str(fov), "--radius", str(int(radius_m)), "--out", name], timeout=300)
    img = case.dir / "work" / name
    if rc != 0 or not img.exists():
        return ToolOut(f"no Street View render: {_tail(out, 1500)}", is_error=True)
    return ToolOut(_tail(out, 1500), [(img, f"Street View near {lat:.5f}, {lon:.5f} (headings {hs})")])


def streetview_sweep(case: Case, lat: float, lon: float, radius_m: int = 3000, provider: str = "mapillary") -> ToolOut:
    """List every panorama in a small area, index them, rank by visual similarity to the photo (MegaLoc)."""
    provider = normalise_pano(provider)
    blocked = pano_block_reason(provider)
    if blocked:
        return ToolOut(blocked, is_error=True)
    radius_m = int(min(max(radius_m, 200), 4400))
    tag = f"sw_{provider}_{lat:.3f}_{lon:.3f}_{radius_m}".replace("-", "m").replace(".", "p")
    rc, out = run_script(case, "pano.py", ["list", "--provider", provider, "--near", _ll(lat, lon),
                                           "--radius", str(radius_m), "--out", f"{tag}.jsonl"], timeout=600)
    man = case.dir / "work" / f"{tag}.jsonl"
    if rc != 0 or not man.exists() or man.stat().st_size == 0:
        return ToolOut(f"no panoramas listed here ({provider}): {_tail(out, 1200)}", is_error=True)
    n = sum(1 for _ in man.open(encoding="utf-8"))
    rc, out = run_script(case, "sweep.py", ["index", "--manifest", f"{tag}.jsonl", "--name", tag], timeout=3600)
    if rc != 0:
        return ToolOut(f"{n} panoramas listed, indexing failed: {_tail(out, 1500)}", is_error=True)
    rc, out = run_script(case, "sweep.py", ["rank", "--index", tag, "--query", str(case.photo), "--top", "15",
                                            "--out-dir", f"{tag}_rank"], timeout=1800)
    rank_dir = case.dir / "work" / f"{tag}_rank"
    sheets = sorted(rank_dir.glob("*.jpg"))[:2] if rank_dir.exists() else []
    return ToolOut(f"{n} panoramas swept.\n{_tail(out, 3500)}",
                   [(s, f"Sweep top matches ({n} panoramas, {radius_m} m around {lat:.4f}, {lon:.4f})") for s in sheets],
                   is_error=rc != 0)


def satellite(case: Case, lat: float, lon: float, zoom: int = 16, source: str = "esri", size: int = 900) -> ToolOut:
    if not SAT_SOURCE.fullmatch(source or ""):
        return ToolOut("unknown source: use esri, google, google-hybrid, bing or wayback:YYYY", is_error=True)
    blocked = satellite_block_reason(source)
    if blocked:
        return ToolOut(blocked, is_error=True)
    zoom = int(min(max(zoom, 3), 20))
    pts = case.dir / "work" / f"pt_{int(time.time() * 1000)}.json"
    pts.parent.mkdir(exist_ok=True)
    pts.write_text(json.dumps({"camera": [lat, lon]}), encoding="utf-8")
    name = f"sat_{lat:.4f}_{lon:.4f}_z{zoom}_{source.replace(':', '-')}.jpg"
    rc, out = run_script(case, "tiles.py", ["sheet", "--points", pts.name, "--zoom", str(int(zoom)), "--size", str(size),
                                            "--cols", "1", "--source", source, "--out", name], timeout=300)
    img = case.dir / "work" / name
    if rc != 0 or not img.exists():
        return ToolOut(f"satellite failed: {_tail(out, 1200)}", is_error=True)
    return ToolOut(f"satellite {source} z{zoom} centred on {lat:.5f}, {lon:.5f}",
                   [(img, f"Satellite ({source}, zoom {zoom}) at {lat:.5f}, {lon:.5f}")])


def terrain_view(case: Case, lat: float, lon: float, heading: float, hfov: float = 70, height_m: float = 2,
                 range_m: int = 30000) -> ToolOut:
    name = f"terrain_{lat:.4f}_{lon:.4f}_h{int(heading)}.jpg"
    rc, out = run_script(case, "terrain.py", ["view", "--at", _ll(lat, lon), "--height", str(height_m),
                                              "--heading", str(heading), "--hfov", str(hfov), "--range", str(int(range_m)),
                                              "--photo", str(case.photo), "--out", name], timeout=600)
    img = case.dir / "work" / name
    if rc != 0 or not img.exists():
        return ToolOut(f"terrain render failed: {_tail(out, 1200)}", is_error=True)
    return ToolOut(_tail(out, 1500), [(img, f"Elevation-model skyline vs photo, camera {lat:.5f}, {lon:.5f}, heading {heading:.0f}°")])


def geocode(query: str, country_code: str = "") -> ToolOut:
    q = {"format": "json", "limit": "6", "q": query}
    if country_code:
        q["countrycodes"] = country_code.lower()
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(q)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "saqr-local-geolocator/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            rows = json.load(r)
    except Exception as e:  # network errors are reported to the agent, not raised
        return ToolOut(f"geocode failed: {e}", is_error=True)
    return ToolOut(json.dumps([{"name": x["display_name"], "lat": float(x["lat"]), "lon": float(x["lon"]),
                                "type": x.get("type"), "bbox": x.get("boundingbox")} for x in rows], ensure_ascii=False))


def osm_query(overpass_ql: str) -> ToolOut:
    data = urllib.parse.urlencode({"data": overpass_ql}).encode()
    for server in ("https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter",
                   "https://overpass.kumi.systems/api/interpreter"):
        try:
            with urllib.request.urlopen(urllib.request.Request(server, data=data,
                                        headers={"User-Agent": "saqr-local-geolocator/1.0"}), timeout=120) as r:
                body = r.read().decode("utf-8", "replace")
            if body.lstrip().startswith("{"):
                return ToolOut(_tail(body, 6000))
        except Exception:
            continue
    return ToolOut("all Overpass servers failed or were busy; a failure is not evidence of absence", is_error=True)


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


# ---------------------------------------------------------------- keyless search (no API key)

LISTING_SITES = ("airbnb.com", "aqar.fm", "bayut.sa", "haraj.com.sa")


def _ddg(query: str, limit: int = 8) -> list[dict]:
    """DuckDuckGo's HTML endpoint: no key, no quota. Returns [{title, url, snippet}]."""
    body = urllib.parse.urlencode({"q": query}).encode()
    req = urllib.request.Request("https://html.duckduckgo.com/html/", data=body,
                                 headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read().decode("utf-8", "replace")
    clean = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s)).strip()
    out = []
    for m in list(re.finditer(r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', page, re.S))[:limit]:
        href = re.search(r'href="([^"]+)"', m.group(0))
        if not href:
            continue
        real = re.search(r"uddg=([^&]+)", href.group(1))
        out.append({"title": clean(m.group(1)),
                    "url": urllib.parse.unquote(real.group(1)) if real else href.group(1), "snippet": ""})
    for row, s in zip(out, re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', page, re.S)):
        row["snippet"] = clean(s)
    return out


def web_lookup(query: str, sites: str = "", limit: int = 8) -> ToolOut:
    """Keyless web search. sites = comma-separated domains, searched one by one."""
    try:
        rows = []
        if sites:
            for s in [x.strip() for x in sites.split(",") if x.strip()][:4]:
                rows += _ddg(f"{query} site:{s}", limit=4)
        else:
            rows = _ddg(query, limit=limit)
    except Exception as e:
        return ToolOut(f"web search failed: {e}", is_error=True)
    return ToolOut(json.dumps(rows, ensure_ascii=False, indent=1) if rows else f"no results for: {query}")


def listing_search(query: str, sites: str = "") -> ToolOut:
    """Rental / property listings: the same photo often sits on Airbnb, aqar.fm, Bayut or Haraj."""
    return web_lookup(query, sites or ",".join(LISTING_SITES))


def gravatar_lookup(case: Case, email: str) -> ToolOut:
    """Gravatar profile for an email (md5 of the address). Free, no key. The avatar is filed so you can compare faces."""
    h = hashlib.md5(email.strip().lower().encode()).hexdigest()
    try:
        req = urllib.request.Request(f"https://gravatar.com/{h}.json", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            entry = (json.load(r).get("entry") or [{}])[0]
    except Exception as e:
        return ToolOut(f"no gravatar profile for {email} ({e})")
    imgs: list[tuple[Path, str]] = []
    try:
        with urllib.request.urlopen(urllib.request.Request(f"https://www.gravatar.com/avatar/{h}?s=400&d=404",
                                                           headers={"User-Agent": UA}), timeout=20) as r:
            avatar = case.dir / "work" / f"gravatar_{h[:8]}.jpg"
            avatar.parent.mkdir(exist_ok=True)
            avatar.write_bytes(r.read())
            imgs.append((avatar, f"Gravatar avatar for {email} — compare with the face in the photo"))
    except Exception:
        pass
    return ToolOut(json.dumps({"email": email, "name": entry.get("displayName") or entry.get("name"),
                               "about": entry.get("aboutMe"), "location": entry.get("currentLocation"),
                               "urls": [u.get("value") for u in (entry.get("urls") or [])]},
                              ensure_ascii=False, indent=1), imgs)
