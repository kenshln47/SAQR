"""The geolocation agent: local recon first, then the AI model drives the geoint tools until it can file one answer."""
from __future__ import annotations

import json
import math
import time
import traceback

import anthropic

from . import openrouter as OR
from . import tools as T
from .cases import Case
from .config import EFFORT, MAX_TURNS, engine_label, has_ai, model_name, provider
from .report import write_report

SYSTEM = """You are SAQR, a photo geolocation analyst running on the user's own computer.
You combine an expert GeoGuessr eye with OSINT discipline: read the image coarse to fine, then prove the
answer with text, web search, maps, street-level imagery and geometry. Never claim more than the evidence supports.

Method
1. Gut call first: from the photo and the recon page, write a ranked shortlist with percentages before using tools.
2. Text is the strongest evidence. Every legible sign, shop name, brand, route number and phone number on a sign or
   shopfront is a search. Use web_search in the local language. Crop the photo (view_photo with a box) to read small
   details. Licence plates count only by their style, colours and country/region code, never by their number.
3. World-prior models (in the recon page) only rank hypotheses; never let them move a pin away from read evidence.
4. List the whole category before choosing (all towns of a region, all covered roads), then let evidence rank it.
5. Narrow before you sweep. streetview_sweep covers at most ~4.4 km radius and costs minutes; use it only once the
   area is small (a town, a road segment). For long rural roads, sample streetview_views along the road instead.
6. Verify: compare invariant features (ridgelines, building outlines, pole positions, curbs), not cars or foliage.
   terrain_view renders the elevation-model skyline for a camera point and heading, stacked over the photo.
   satellite shows the camera area from above. Each confirmed match should leave an evidence image.
7. Leave a little room. A city can be filed from one strong cluster (readable text, or architecture plus climate) without waiting for a second independent constraint. For lookalike Gulf cities (Riyadh, Dubai, Doha, Abu Dhabi), compare them in the shortlist and put the rejected ones in alternatives; never default to the most famous skyline.
   A street answer is allowed from one strong clue: a unique readable place name, or a street-level match on 2 features, with medium confidence and an honest radius.
   A radius under 100 m needs a street-level match on at least 2 features, or one name that geocodes to a single place. If that bar is missed, widen the radius and still file the best area. Do not invent a building pin for a generic landscape.
8. Never fabricate verification. If you did not run the tool, the claim is an unverified estimate.
9. One answer, no midpoints between rival candidates. Put rivals in alternatives with the test that separates them.

Map: call pin_candidate for every serious candidate as you go (the user watches the map fill in).
Finish: always call final_answer exactly once, even when evidence is thin; uncertainty goes into confidence and radius.
Write the summary, clues and alternatives in Gulf Arabic, concise. Place names may stay in their local form.

Limits you must keep
- Do not geolocate a private person's home, school or routine. If the photo centres on private individuals or the
  inside/outside of a private home, stop at city level, say why in the summary, and do not pin the building.
- Never read out, search or record a licence plate number, and never use it to identify a vehicle or its owner.
- Public places, landscapes, news events, game screenshots and the user's own photos are fine to pin precisely.
"""

PRIVATE_NOTE = """

Private-place mode (this run)
The "stop at city level" rule above is relaxed here. Start from the city, then climb only as far as the evidence:
1. Text first: a shop sign next door, a street name plate, a building number, a delivery sticker, a mail envelope,
   a school badge or gate sign. Every one of them is a search in the local language.
2. Architecture plus a mapped footprint (satellite, OSM building outlines) for a detached house or a school block.
3. Interiors: the view out of the window, the skyline, the neighbourhood layout, finishes and furniture.
4. Reverse search and listing_search: an Airbnb, aqar.fm, Bayut or Haraj listing often carries the same photo,
   the same window view and the address.
Pin the building and set level="point" only when a listing or a text anchor ties that building to the photo.
Otherwise file the best district and say plainly in the summary why the building could not be pinned.
A school: geocode and osm_query (amenity=school) inside the city, then match badge, uniform, gate, fence and colours.
A routine photo ("where does this person go every day"): name the place and, when it fits, the exact branch.
The family car's plate number may be read and searched here as an extra anchor; do not lean on it alone.
Never invent a building. An honest district beats a confident wrong door.
"""

MODE_HINT = {
    "region": "Mode: FIND REGION (quick). Aim for country, region and city with an honest radius. Use at most ~12 tool calls.",
    "street": ("Mode: FIND STREET (deep). Push to the street or camera point when the evidence allows: narrow, then "
               "street-level checks, sweeps, terrain and satellite evidence. Stop when one strong constraint is confirmed, or two weaker ones agree. If neither holds, still file the best city or district with a wider radius."),
    "private": ("Mode: PRIVATE PLACE (بيت · مدرسة · شغل · روتين). The subject is a private home, a school or ordinary "
                "people, so push past the city when the evidence allows. Same tools, deeper ladder."),
}

NUM = {"type": "number"}
TOOLS = [
    {"name": "view_photo", "description": "Look at the original photo again, optionally a pixel crop to read small text or objects.",
     "input_schema": {"type": "object", "properties": {"box": {"type": "array", "items": {"type": "integer"},
                      "description": "x0,y0,x1,y1 in original pixels; omit for the full photo"}}, "additionalProperties": False}},
    {"name": "streetview_near", "description": "Nearest Google Street View panorama (id, coordinates, date, road). Refused unless SAQR_GOOGLE_KEY or GOOGLE_MAPS_API_KEY is set; otherwise use streetview_sweep.",
     "input_schema": {"type": "object", "properties": {"lat": NUM, "lon": NUM, "radius_m": {"type": "integer"}},
                      "required": ["lat", "lon"], "additionalProperties": False}},
    {"name": "streetview_views", "description": "Render Google Street View around a point, one heading per frame, as one sheet. Same key requirement as streetview_near.",
     "input_schema": {"type": "object", "properties": {"lat": NUM, "lon": NUM, "headings": {"type": "array", "items": NUM},
                      "pitch": NUM, "fov": NUM, "radius_m": {"type": "integer"}}, "required": ["lat", "lon"], "additionalProperties": False}},
    {"name": "streetview_sweep", "description": ("Index every panorama within radius_m (≤4400) of a point and rank them by visual similarity "
                                                 "to the photo (MegaLoc). Slow (minutes). Default provider is mapillary. "
                                                 "Also open: kartaview, panoramax. google, apple, bing and yandex are refused unless their own key is set."),
     "input_schema": {"type": "object", "properties": {"lat": NUM, "lon": NUM, "radius_m": {"type": "integer"},
                      "provider": {"type": "string"}}, "required": ["lat", "lon"], "additionalProperties": False}},
    {"name": "satellite", "description": "Satellite tile mosaic centred on a point. Sources: esri, bing, wayback:YYYY. google and google-hybrid need SAQR_GOOGLE_KEY or GOOGLE_MAPS_API_KEY.",
     "input_schema": {"type": "object", "properties": {"lat": NUM, "lon": NUM, "zoom": {"type": "integer"}, "source": {"type": "string"}},
                      "required": ["lat", "lon"], "additionalProperties": False}},
    {"name": "terrain_view", "description": "Render the elevation-model skyline seen from a camera point and heading, stacked over the photo for comparison.",
     "input_schema": {"type": "object", "properties": {"lat": NUM, "lon": NUM, "heading": NUM, "hfov": NUM, "height_m": NUM,
                      "range_m": {"type": "integer"}}, "required": ["lat", "lon", "heading"], "additionalProperties": False}},
    {"name": "geocode", "description": "Look up a place name (OpenStreetMap Nominatim). Returns candidates with coordinates and bounding boxes.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "country_code": {"type": "string"}},
                      "required": ["query"], "additionalProperties": False}},
    {"name": "osm_query", "description": "Run an Overpass QL query against OpenStreetMap (roads, landmarks, power lines…). Use [out:json] and out center.",
     "input_schema": {"type": "object", "properties": {"overpass_ql": {"type": "string"}}, "required": ["overpass_ql"], "additionalProperties": False}},
    {"name": "listing_search", "description": "Search rental/property listings (Airbnb, aqar.fm, Bayut, Haraj) for text or features seen in the photo, to match an interior or a facade to a listing.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "sites": {"type": "string", "description": "comma-separated domains; omit for the defaults"}},
                      "required": ["query"], "additionalProperties": False}},
    {"name": "pin_candidate", "description": "Put a candidate location on the user's map with your confidence and why.",
     "input_schema": {"type": "object", "properties": {"lat": NUM, "lon": NUM, "label": {"type": "string"},
                      "confidence": {"type": "number", "description": "0-1"}, "radius_km": NUM, "reason": {"type": "string"}},
                      "required": ["lat", "lon", "label", "confidence", "radius_km", "reason"], "additionalProperties": False}},
    {"name": "final_answer", "description": "File the single best answer. Call exactly once, at the end.",
     "input_schema": {"type": "object", "properties": {
         "country": {"type": "string"}, "region": {"type": "string"}, "city": {"type": "string"},
         "lat": NUM, "lon": NUM, "radius_km": NUM,
         "level": {"type": "string", "enum": ["country", "region", "city", "street", "point"]},
         "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
         "summary": {"type": "string", "description": "Gulf Arabic, 2-5 sentences"},
         "clues": {"type": "array", "items": {"type": "string"}},
         "alternatives": {"type": "array", "items": {"type": "object", "properties": {
             "place": {"type": "string"}, "lat": NUM, "lon": NUM, "why": {"type": "string"}},
             "required": ["place", "why"], "additionalProperties": False}},
         "unverified": {"type": "array", "items": {"type": "string"}}},
         "required": ["country", "lat", "lon", "radius_km", "level", "confidence", "summary", "clues"],
         "additionalProperties": False}},
]
for _t in TOOLS:
    _t["eager_input_streaming"] = True
SERVER_TOOLS = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 10}]


def _valid(name: str, inp) -> str | None:
    """The streamed tool input is not validated by the API; check required keys and number types ourselves."""
    spec = next((t for t in TOOLS if t["name"] == name), None)
    if spec is None:
        return f"unknown tool {name}"
    if not isinstance(inp, dict):
        return "tool input must be a JSON object"
    schema = spec["input_schema"]
    for k in schema.get("required", []):
        if k not in inp:
            return f"missing required field '{k}'"
    for k, v in inp.items():
        prop = schema["properties"].get(k, {})
        typ = prop.get("type")
        if typ in ("number", "integer") and (not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v)):
            return f"field '{k}' must be a number"
        if "enum" in prop and v not in prop["enum"]:
            return f"field '{k}' must be one of {prop['enum']}"
    if "lat" in inp and not -90 <= inp["lat"] <= 90:
        return "lat must be between -90 and 90"
    if "lon" in inp and not -180 <= inp["lon"] <= 180:
        return "lon must be between -180 and 180"
    return None


def _friendly(e: Exception) -> str:
    """Arabic explanation for the errors people actually hit; the raw error stays in the trace."""
    t = f"{type(e).__name__}: {e}"
    low = t.lower()
    if "authentication" in low or " 401" in low or "invalid x-api-key" in low or "user not found" in low:
        return "المفتاح مرفوض: افتح الإعدادات وتأكد منه"
    if " 402" in low or "credit" in low or "billing" in low or "insufficient" in low:
        return "رصيدك عند المزود خلص أو ما يكفي: اشحن الرصيد وأعد التحليل"
    if " 429" in low or ("rate" in low and "limit" in low) or "overloaded" in low:
        return "المزود مشغول أو وصلت حد الاستخدام: استنى شوي وأعد التحليل"
    if "connection" in low or "timed out" in low or "timeout" in low or "getaddrinfo" in low:
        return "ما قدرت أوصل للمزود: تأكد من الإنترنت وأعد التحليل"
    if "unidentifiedimage" in low or "cannot identify image" in low:
        return "ما قدرت أفتح الصورة: جرب تحفظها JPG وترفعها من جديد"
    return t[:400]


def _image_holders(content):
    """Every image part in a message body, including the ones nested inside Anthropic tool_result blocks."""
    for part in content if isinstance(content, list) else []:
        if not isinstance(part, dict):
            continue
        if part.get("type") in ("image", "image_url"):
            yield part
        elif part.get("type") == "tool_result" and isinstance(part.get("content"), list):
            yield from (x for x in part["content"] if isinstance(x, dict) and x.get("type") in ("image", "image_url"))


def _prune_images(messages: list, keep: int = 6) -> None:
    """Keep the newest tool images; older ones become a note (they stay in the evidence tab),
    so long runs do not resend every image every turn or overflow the context."""
    seen = 0
    for m in reversed(messages):
        if not isinstance(m, dict) or m.get("role") != "user":
            continue
        for part in list(_image_holders(m.get("content"))):
            seen += 1
            if seen > keep:
                part.clear()
                part.update({"type": "text", "text": "[older image removed to save context; it is in the case evidence]"})


def _run_tool(case: Case, name: str, inp: dict) -> T.ToolOut:
    if name == "view_photo":
        return T.view_photo(case, inp.get("box"))
    if name == "streetview_near":
        return T.streetview_near(case, inp["lat"], inp["lon"], inp.get("radius_m", 200))
    if name == "streetview_views":
        return T.streetview_views(case, inp["lat"], inp["lon"], inp.get("headings"), inp.get("pitch", 0),
                                  inp.get("fov", 90), inp.get("radius_m", 300))
    if name == "streetview_sweep":
        return T.streetview_sweep(case, inp["lat"], inp["lon"], inp.get("radius_m", 3000), inp.get("provider") or "mapillary")
    if name == "satellite":
        return T.satellite(case, inp["lat"], inp["lon"], inp.get("zoom", 16), inp.get("source", "esri"))
    if name == "terrain_view":
        return T.terrain_view(case, inp["lat"], inp["lon"], inp["heading"], inp.get("hfov", 70), inp.get("height_m", 2),
                              inp.get("range_m", 30000))
    if name == "geocode":
        return T.geocode(inp["query"], inp.get("country_code", ""))
    if name == "osm_query":
        return T.osm_query(inp["overpass_ql"])
    if name == "listing_search":
        return T.listing_search(inp["query"], inp.get("sites", ""))
    if name == "pin_candidate":
        case.add_candidate({k: inp[k] for k in ("lat", "lon", "label", "confidence", "radius_km", "reason")})
        return T.ToolOut("pinned")
    if name == "final_answer":
        case.update(final=inp)
        case.emit("final", final=inp)
        return T.ToolOut("filed")
    return T.ToolOut(f"unknown tool {name}", is_error=True)


def _tool_result(case: Case, block, out: T.ToolOut) -> dict:
    content: list[dict] = [{"type": "text", "text": out.text or "(no output)"}]
    for path, caption in out.images:
        if path.exists():
            case.add_evidence(path, caption)
            content.append(T.image_block(path))
    return {"type": "tool_result", "tool_use_id": block.id, "content": content, "is_error": out.is_error}


def _prior_candidates(case: Case) -> None:
    """Put the model's ranking on the map so the user sees something even before (or without) Claude."""
    pj = T.prior_json(case)
    if not pj:
        return
    countries = ", ".join(f"{c['name']} {round(c['p'] * 100)}%" for c in (pj.get("combined") or [])[:5])
    if countries:
        case.emit("log", text=f"توقع النماذج المحلية للدولة: {countries}")
    bg = pj.get("best_guess") or {}
    if "lat" in bg:
        case.add_candidate({"lat": bg["lat"], "lon": bg["lon"], "label": f"تخمين النماذج · {bg.get('near', '')}",
                            "confidence": round(float((pj.get("assessment") or {}).get("top_p", 0.2)), 2),
                            "radius_km": 300, "reason": "ترتيب GeoCLIP و StreetCLIP (منطقة بداية، متوسط الخطأ ~270 كم)",
                            "source": "model"})


def _local_clues(case: Case, pj: dict) -> list[str]:
    """Plain-Arabic summary of what the local recon actually found, for the no-key result card."""
    out = []
    top = ", ".join(f"{c['name']} {round(c['p'] * 100)}%" for c in (pj.get("combined") or [])[:4])
    if top:
        out.append(f"توقع النماذج المحلية للدولة: {top}")
    bg = pj.get("best_guess") or {}
    if "lat" in bg:
        out.append(f"أقوى تجمع في GeoCLIP قرب {bg.get('near', '?')} ({bg['lat']:.2f}, {bg['lon']:.2f}) · متوسط خطأ هالنماذج ~270 كم")
    if (pj.get("assessment") or {}).get("informative") is False:
        out.append("الصورة فقيرة بالتفاصيل، فالتخمين ضعيف حتى على مستوى الدولة")
    work = case.dir / "work" / "recon"
    try:
        meta = json.loads((work / "meta" / "meta.json").read_text(encoding="utf-8")).get("digest", {})
        gps, when = meta.get("gps") or {}, meta.get("time") or {}
        out.append(f"فيه GPS في ملف الصورة: {gps}" if gps else "ما فيه GPS في ملف الصورة (طبيعي للصور المرسلة أو المحفوظة من النت)")
        if when:
            out.append(f"وقت التصوير في الملف: {when}")
    except (OSError, ValueError):
        pass
    try:
        items = json.loads((work / "intake" / "ocr.json").read_text(encoding="utf-8")).get("items") or []
        texts = [str(i.get("text", "")).strip() for i in items if str(i.get("text", "")).strip()]
        out.append(f"نص مقروء في الصورة: {' · '.join(texts[:6])}" if texts else "ما فيه نص مقروء في الصورة")
    except (OSError, ValueError):
        pass
    return out


def finish(case: Case, status: str, text: str, error: str = "") -> None:
    """Close a run the same way everywhere: report, final status, last stage event."""
    try:
        write_report(case)
    except Exception as e:   # a broken report must not hide the result
        case.emit("log", text=f"ما قدرت أكتب التقرير: {e}")
    if status == "error":
        case.update(status="error", error=error or text)
        case.emit("error", text=error or text)
    else:
        case.update(status=status)
        case.emit("stage", stage="done", text=text)


def run_geolocate(case: Case, mode: str) -> None:
    try:
        rev = case.load().get("rev", True)
        case.update(status="recon", engine=engine_label() if has_ai() else "local")
        steps = "بيانات الملف · قراءة النص · كشف العناصر · توقع النماذج" + (" · بحث عكسي أونلاين (Yandex و Baidu)" if rev else "")
        case.emit("stage", stage="recon", text=f"الفحص الأولي: {steps}")
        rec = T.recon(case)
        for p, cap in rec.images:
            case.add_evidence(p, cap)
        case.emit("log", text="خلص الفحص الأولي" if not rec.is_error else "الفحص الأولي فيه أخطاء (نكمل)")
        _prior_candidates(case)
        if case.cancelled():
            return finish(case, "stopped", "انوقف بطلبك")

        if not has_ai():
            pj = T.prior_json(case) or {}
            bg = pj.get("best_guess") or {}
            top = (pj.get("combined") or [{}])[0]
            if "lat" not in bg or not top.get("name"):
                return finish(case, "error", "",
                              "الفحص المحلي ما رجع تخمين موقع. توقع الدولة (StreetCLIP) غير تجاري ومطفأ "
                              "إلا إذا ضبطت SAQR_ALLOW_NC_MODELS=1 على جهاز شخصي. "
                              "أضف مفتاح من الإعدادات للتحليل الكامل، أو شوف السجل.")
            final = {"country": top["name"], "region": "", "city": bg.get("near", ""),
                     "lat": bg["lat"], "lon": bg["lon"], "radius_km": 300, "level": "country",
                     "confidence": "low",
                     "summary": "وضع محلي بدون ذكاء اصطناعي: هذا تخمين نماذج التعرف المحلية فقط (GeoCLIP + StreetCLIP). "
                                "أضف مفتاح OpenRouter أو Anthropic من الإعدادات عشان يشتغل التحليل الكامل والتحقق.",
                     "clues": _local_clues(case, pj), "alternatives": [],
                     "unverified": ["ما فيه خطوة تفكير وتحقق: هذا ترتيب النماذج بس، والنقطة على الخريطة منطقة بداية مو جواب"]}
            case.update(final=final)
            case.emit("final", final=final)
            return finish(case, "done", "خلص (نماذج محلية بس)")

        case.update(status="analysing")
        case.emit("stage", stage="analysis", text=f"{engine_label()} يحلل الأدلة ويتحقق")
        if provider() == "openrouter":
            _agent_loop_openrouter(case, mode, rec.text)
        else:
            _agent_loop(case, mode, rec.text)
        if case.load().get("final"):
            finish(case, "done", "خلص")
        elif case.cancelled():
            finish(case, "stopped", "انوقف بطلبك قبل الجواب النهائي")
        else:
            finish(case, "error", "", "خلص التحليل بدون جواب نهائي (رفض أو انتهت الجولات). المرشحات على الخريطة باقية.")
    except Exception as e:
        case.emit("log", text=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-2000:])
        finish(case, "error", "", _friendly(e))


def _intro(case: Case, mode: str, recon_md: str) -> str:
    w, h = T.photo_size(case)
    return (f"{MODE_HINT.get(mode, MODE_HINT['region'])}\n\nWhere was this photo taken?\n"
            f"The photo is {w}x{h} px (the copy you see may be downscaled; view_photo boxes use the full size).\n\n"
            f"<recon>\n{recon_md[:20000]}\n</recon>")


def _stop_requested(case: Case) -> bool:
    if case.cancelled():
        case.emit("log", text="انوقف التحليل بطلبك")
        return True
    return False


def _show_result(case: Case, name: str, out: T.ToolOut) -> None:
    if name not in ("pin_candidate", "final_answer"):
        case.emit("result", name=name, text=(out.text or "")[:600], error=out.is_error)


def _stream_with_retry(client, **kw):
    for attempt in range(3):
        try:
            with client.beta.messages.stream(**kw) as stream:
                return stream.get_final_message()
        except (anthropic.APIConnectionError, anthropic.InternalServerError, anthropic.RateLimitError):
            if attempt == 2:
                raise
            time.sleep(15 * (attempt + 1))


def _agent_loop(case: Case, mode: str, recon_md: str) -> None:
    client = anthropic.Anthropic()
    model = model_name()   # fixed for the whole run, even if Settings change meanwhile
    system = PRIVATE_NOTE if mode == "private" else SYSTEM
    messages: list[dict] = [{"role": "user", "content": [
        T.image_block(case.photo), {"type": "text", "text": _intro(case, mode, recon_md)}]}]
    nudged = False
    for turn in range(MAX_TURNS):
        if _stop_requested(case):
            return
        case.emit("progress", turn=turn + 1, max=MAX_TURNS)
        _prune_images(messages[1:])
        msg = _stream_with_retry(
            client, model=model, max_tokens=64000, system=system, tools=TOOLS + SERVER_TOOLS, messages=messages,
            thinking={"type": "adaptive", "display": "summarized"}, output_config={"effort": EFFORT},
            cache_control={"type": "ephemeral"},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        )

        for b in msg.content:
            if b.type == "thinking" and getattr(b, "thinking", ""):
                case.emit("thinking", text=b.thinking)
            elif b.type == "text" and b.text.strip():
                case.emit("say", text=b.text)
            elif b.type == "server_tool_use":
                case.emit("tool", name=b.name, input=b.input)
        messages.append({"role": "assistant", "content": msg.content})

        if msg.stop_reason == "refusal":
            case.emit("log", text="النموذج رفض يكمل هالطلب")
            return
        if msg.stop_reason == "pause_turn":
            continue
        uses = [b for b in msg.content if b.type == "tool_use"]
        if msg.stop_reason == "max_tokens" and not uses:
            messages.append({"role": "user", "content": "Continue, then call final_answer."})
            continue
        if not uses:
            if case.load().get("final") or nudged:
                return
            nudged = True
            messages.append({"role": "user", "content": "Call final_answer now with your best single answer."})
            continue

        results = []
        for b in uses:
            err = _valid(b.name, b.input)
            if err:
                results.append({"type": "tool_result", "tool_use_id": b.id, "is_error": True,
                                "content": f"INVALID_INPUT: {err}. Re-issue the call with a complete JSON object."})
                continue
            case.emit("tool", name=b.name, input=b.input)
            try:
                out = _run_tool(case, b.name, b.input)
            except Exception as e:
                out = T.ToolOut(f"{type(e).__name__}: {e}", is_error=True)
            _show_result(case, b.name, out)
            results.append(_tool_result(case, b, out))
        messages.append({"role": "user", "content": results})
        if case.load().get("final"):
            return
    case.emit("log", text=f"وقف بعد {MAX_TURNS} جولة")


WEB_SEARCH_OR = {"type": "openrouter:web_search", "parameters": {"max_results": 5, "max_uses": 10}}


def _agent_loop_openrouter(case: Case, mode: str, recon_md: str) -> None:
    """Same loop over OpenRouter's OpenAI-style API. Tool messages carry text only, so the images a tool made
    follow in one user message after the tool results."""
    model = model_name()
    tools = OR.function_tools(TOOLS) + [WEB_SEARCH_OR]
    system = PRIVATE_NOTE if mode == "private" else SYSTEM
    messages: list[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": [
            OR.image_part(T.image_block(case.photo)), {"type": "text", "text": _intro(case, mode, recon_md)}]},
    ]
    nudged = False
    for turn in range(MAX_TURNS):
        if _stop_requested(case):
            return
        case.emit("progress", turn=turn + 1, max=MAX_TURNS)
        _prune_images(messages[2:])
        resp = OR.chat(model=model, messages=messages, tools=tools, max_tokens=32000, max_tool_calls=12,
                       **OR.reasoning(model, EFFORT))
        choice = (resp.get("choices") or [{}])[0]
        msg, finish = choice.get("message") or {}, choice.get("finish_reason")
        if isinstance(msg.get("reasoning"), str) and msg["reasoning"].strip():
            case.emit("thinking", text=msg["reasoning"][-6000:])
        if (msg.get("content") or "").strip():
            case.emit("say", text=msg["content"])
        cites = [a for a in msg.get("annotations") or [] if a.get("type") == "url_citation"]
        if cites:
            case.emit("tool", name="web_search", input={"sources": len(cites)})
        calls = msg.get("tool_calls") or []
        kept = {"role": "assistant", "content": msg.get("content") or ""}
        if calls:
            kept["tool_calls"] = calls
        if msg.get("reasoning_details"):
            kept["reasoning_details"] = msg["reasoning_details"]
        messages.append(kept)

        if finish == "content_filter" or msg.get("refusal"):
            case.emit("log", text="النموذج رفض يكمل هالطلب")
            return
        if finish == "length" and not calls:
            messages.append({"role": "user", "content": "Continue, then call final_answer."})
            continue
        if not calls:
            if case.load().get("final") or nudged:
                return
            nudged = True
            messages.append({"role": "user", "content": "Call final_answer now with your best single answer."})
            continue

        pictures: list[dict] = []
        for c in calls:
            name = c.get("function", {}).get("name", "")
            try:
                inp = json.loads(c.get("function", {}).get("arguments") or "{}")
            except json.JSONDecodeError:
                inp = None
            err = "arguments were not valid JSON" if inp is None else _valid(name, inp)
            if err:
                messages.append({"role": "tool", "tool_call_id": c["id"],
                                 "content": f"INVALID_INPUT: {err}. Re-issue the call with a complete JSON object."})
                continue
            case.emit("tool", name=name, input=inp)
            try:
                out = _run_tool(case, name, inp)
            except Exception as e:
                out = T.ToolOut(f"{type(e).__name__}: {e}", is_error=True)
            _show_result(case, name, out)
            text = out.text or "(no output)"
            for path, caption in out.images:
                if path.exists():
                    case.add_evidence(path, caption)
                    pictures += [{"type": "text", "text": f"[{name}] {caption}"}, OR.image_part(T.image_block(path))]
            if out.images:
                text += f"\n({len(out.images)} image(s) follow in the next message)"
            messages.append({"role": "tool", "tool_call_id": c["id"], "content": ("ERROR: " if out.is_error else "") + text})
        if pictures:
            messages.append({"role": "user", "content": [{"type": "text", "text": "Images from the tool calls above:"}, *pictures]})
        if case.load().get("final"):
            return
    case.emit("log", text=f"وقف بعد {MAX_TURNS} جولة")
