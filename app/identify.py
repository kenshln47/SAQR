"""Identity modules: who is this person (photo and/or email/phone/name), and what a licence plate says.

Each module runs its own short agent loop over its own tools and files one answer.
agent.py's geolocation loop is not touched.
"""
from __future__ import annotations

import json
import re
import traceback
from pathlib import Path

import anthropic

from . import openrouter as OR
from . import tools as T
from .agent import _friendly, _stream_with_retry, finish
from .cases import Case
from .config import EFFORT, MAX_TURNS, engine_label, has_ai, model_name, provider

WEB_SEARCH_OR = {"type": "openrouter:web_search", "parameters": {"max_results": 5, "max_uses": 8}}
SERVER_WEB = {"type": "web_search_20260209", "name": "web_search", "max_uses": 8}
STR = {"type": "string"}

VIEW = {"name": "view_photo",
        "description": "Look at the photo again, optionally a pixel crop (box) to read a plate, a badge or a small detail.",
        "input_schema": {"type": "object", "properties": {"box": {"type": "array", "items": {"type": "integer"},
                          "description": "x0,y0,x1,y1 in original pixels"}}, "additionalProperties": False}}

WEB = {"name": "web_lookup",
       "description": "Keyless web search (DuckDuckGo). sites = comma-separated domains to search one by one, e.g. 'linkedin.com,github.com'.",
       "input_schema": {"type": "object", "properties": {"query": STR, "sites": STR}, "required": ["query"],
                        "additionalProperties": False}}

GRAV = {"name": "gravatar_lookup",
        "description": "Gravatar profile for an email: display name, location, the person's other accounts, and the avatar image so you can compare it with the face in the photo.",
        "input_schema": {"type": "object", "properties": {"email": STR}, "required": ["email"], "additionalProperties": False}}

ACCOUNT = {"type": "object", "properties": {"site": STR, "handle": STR, "url": STR, "why": STR},
           "required": ["site", "why"], "additionalProperties": False}

FILE_PERSON = {"name": "file_person", "description": "File the single best identification. Call exactly once, at the end.",
    "input_schema": {"type": "object", "properties": {
        "found": {"type": "boolean", "description": "true only when a real person was actually identified"},
        "name": STR, "role": STR, "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "summary": STR, "place": STR, "accounts": {"type": "array", "items": ACCOUNT},
        "evidence": {"type": "array", "items": STR}, "unverified": {"type": "array", "items": STR}},
        "required": ["found", "name", "role", "confidence", "summary", "accounts", "evidence"],
        "additionalProperties": False}}

FILE_PLATE = {"name": "file_plate", "description": "File the plate reading and everything the plate supports. Call exactly once, at the end.",
    "input_schema": {"type": "object", "properties": {
        "plate": {"type": "string", "description": "the plate as written, letters and digits"},
        "country": STR, "plate_type": STR, "region_hint": STR,
        "vehicle": {"type": "string", "description": "make, model, year range if visible"},
        "owner": {"type": "string", "description": "owner name if the evidence supports it, else empty"},
        "owner_note": {"type": "string", "description": "why the owner is or is not knowable"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]}, "summary": STR,
        "evidence": {"type": "array", "items": STR}, "unverified": {"type": "array", "items": STR}},
        "required": ["plate", "country", "vehicle", "confidence", "summary", "evidence"],
        "additionalProperties": False}}

PERSON_TOOLS = [VIEW, WEB, GRAV, FILE_PERSON]
PLATE_TOOLS = [VIEW, WEB, FILE_PLATE]

SYSTEM_PERSON = """You are SAQR's identity analyst, running on the user's own computer.
You identify a person from whatever you are given: a photo, an email, a phone number, a name, or a mix.

Method
- web_lookup is a real search engine and needs no key. Use it for everything, in the local language of the lead.
  Use web_search too when the run has it.
- Email: the part before @ is a handle. Search it as a handle, as "user@domain", and with site: filters
  (linkedin.com, github.com, x.com, instagram.com, facebook.com). The domain alone can be the employer or the school.
  Always call gravatar_lookup on the address: a Gravatar profile lists the person's other accounts, and its avatar
  is shown to you so you can compare it with the face in the photo.
- Phone: search the full number, the number without the country code, and the number in quotes. Read the country code
  first (966 = Saudi Arabia). Numbers surface in business listings, marketplaces and ads.
- Name: search the name plus any constraint you can see (city, uniform, employer, school, sport, age). A common name
  with no second constraint is a candidate, not an answer.
- Photo: describe the face, the age band, the dress, any uniform or badge, and the background; search those with the name.
  A face alone identifies a public figure well, and a private person only if the photo is on the web.
- Verification: an account counts only when the search result actually ties it to this person. Do not merge two people
  with the same name. Never present a guess as a fact.

Finish by calling file_person exactly once, even when the evidence is thin (say so in unverified).
Write summary, role and every why in Gulf Arabic, concise. Handles and URLs stay as they are."""

SYSTEM_PLATE = """You read a vehicle licence plate from a photo and report what the plate actually supports.

Method
1. Find the plate and crop it with view_photo (a tight box, then a wider one if it is blurry). Read it character by
   character: the digits, the letters in their own script, and the country or region marking. Say what you are unsure of.
2. Identify the vehicle from the grille, lamps, badges and body (make, model, year range).
3. The plate style, colours and country code are location and era clues: private, commercial, taxi, diplomatic,
   export. Use web_lookup to confirm what the format means.
4. Search the plate itself: the digits and letters together, and the digits with the vehicle. Cars appear in
   marketplaces and forums with their plate.
5. On the owner: in Saudi Arabia the owner's name is not public from the plate alone. Say so plainly, name the route
   (Absher / Mojaz) when the country is Saudi, and only give an owner name when a listing or a page really shows one.

Never invent a character you cannot read; a partially read plate is still useful. Say which characters are certain.
Finish by calling file_plate exactly once. Write summary, vehicle and owner_note in Gulf Arabic."""


def _valid(tools, name: str, inp) -> str | None:
    spec = next((t for t in tools if t["name"] == name), None)
    if spec is None:
        return f"unknown tool {name}"
    if not isinstance(inp, dict):
        return "tool input must be a JSON object"
    for k in spec["input_schema"].get("required", []):
        if k not in inp:
            return f"missing required field '{k}'"
    return None


def _show(case: Case, name: str, out: T.ToolOut) -> None:
    if not name.startswith("file_"):
        case.emit("result", name=name, text=(out.text or "")[:600], error=out.is_error)


def _run_tool(case: Case, name: str, inp: dict) -> T.ToolOut:
    if name == "view_photo":
        return T.view_photo(case, inp.get("box"))
    if name == "web_lookup":
        return T.web_lookup(inp["query"], inp.get("sites", ""))
    if name == "gravatar_lookup":
        return T.gravatar_lookup(case, inp["email"])
    if name.startswith("file_"):
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


def _agent(case: Case, system: str, tools: list[dict], intro: str, image: Path | None, file_tool: str) -> None:
    """Short single-answer loop over our own tools, on whichever provider is configured."""
    model, use_or = model_name(), provider() == "openrouter"
    if use_or:
        body = ([OR.image_part(T.image_block(image))] if image else []) + [{"type": "text", "text": intro}]
        messages = [{"role": "system", "content": system}, {"role": "user", "content": body}]
        api_tools = OR.function_tools(tools) + [WEB_SEARCH_OR]
    else:
        client = anthropic.Anthropic()
        body = ([T.image_block(image)] if image else []) + [{"type": "text", "text": intro}]
        messages = [{"role": "user", "content": body}]
        api_tools = tools + [SERVER_WEB]
    nudged = False
    for turn in range(MAX_TURNS):
        if case.cancelled():
            case.emit("log", text="انوقف التحليل بطلبك")
            return
        case.emit("progress", turn=turn + 1, max=MAX_TURNS)
        case.add_cost(turns=1)
        if use_or:
            resp = OR.chat(model=model, messages=messages, tools=api_tools, max_tokens=16000, max_tool_calls=10,
                           **OR.reasoning(model, EFFORT))
            choice = (resp.get("choices") or [{}])[0]
            msg, why = choice.get("message") or {}, choice.get("finish_reason")
            if isinstance(msg.get("reasoning"), str) and msg["reasoning"].strip():
                case.emit("thinking", text=msg["reasoning"][-6000:])
            if (msg.get("content") or "").strip():
                case.emit("say", text=msg["content"])
            calls = msg.get("tool_calls") or []
            kept = {"role": "assistant", "content": msg.get("content") or ""}
            if calls:
                kept["tool_calls"] = calls
            if msg.get("reasoning_details"):
                kept["reasoning_details"] = msg["reasoning_details"]
            messages.append(kept)
            if why == "content_filter" or msg.get("refusal"):
                case.emit("log", text="النموذج رفض يكمل هالطلب")
                return
            if not calls:
                if case.load().get("final") or nudged:
                    return
                nudged = True
                messages.append({"role": "user", "content": f"Call {file_tool} now with your best answer."})
                continue
            pictures: list[dict] = []
            for c in calls:
                name = c.get("function", {}).get("name", "")
                try:
                    inp = json.loads(c.get("function", {}).get("arguments") or "{}")
                except json.JSONDecodeError:
                    inp = None
                err = "arguments were not valid JSON" if inp is None else _valid(tools, name, inp)
                if err:
                    messages.append({"role": "tool", "tool_call_id": c["id"], "content": f"INVALID_INPUT: {err}"})
                    continue
                case.emit("tool", name=name, input=inp)
                case.add_cost(tools=1)
                try:
                    out = _run_tool(case, name, inp)
                except Exception as e:
                    out = T.ToolOut(f"{type(e).__name__}: {e}", is_error=True)
                _show(case, name, out)
                text = out.text or "(no output)"
                for path, caption in out.images:
                    if path.exists():
                        case.add_evidence(path, caption)
                        pictures += [{"type": "text", "text": f"[{name}] {caption}"}, OR.image_part(T.image_block(path))]
                if out.images:
                    text += f"\n({len(out.images)} image(s) follow in the next message)"
                messages.append({"role": "tool", "tool_call_id": c["id"],
                                 "content": ("ERROR: " if out.is_error else "") + text})
            if pictures:
                messages.append({"role": "user", "content": [{"type": "text", "text": "Images from the tool calls above:"}, *pictures]})
        else:
            msg = _stream_with_retry(client, model=model, max_tokens=16000, system=system, tools=api_tools,
                                     messages=messages, thinking={"type": "adaptive", "display": "summarized"},
                                     output_config={"effort": EFFORT})
            for b in msg.content:
                if b.type == "thinking" and getattr(b, "thinking", ""):
                    case.emit("thinking", text=b.thinking)
                elif b.type == "text" and b.text.strip():
                    case.emit("say", text=b.text)
            messages.append({"role": "assistant", "content": msg.content})
            if msg.stop_reason == "refusal":
                case.emit("log", text="النموذج رفض يكمل هالطلب")
                return
            uses = [b for b in msg.content if b.type == "tool_use"]
            if not uses:
                if case.load().get("final") or nudged:
                    return
                nudged = True
                messages.append({"role": "user", "content": f"Call {file_tool} now with your best answer."})
                continue
            results = []
            for b in uses:
                err = _valid(tools, b.name, b.input)
                if err:
                    results.append({"type": "tool_result", "tool_use_id": b.id, "is_error": True,
                                    "content": f"INVALID_INPUT: {err}"})
                    continue
                case.emit("tool", name=b.name, input=b.input)
                case.add_cost(tools=1)
                try:
                    out = _run_tool(case, b.name, b.input)
                except Exception as e:
                    out = T.ToolOut(f"{type(e).__name__}: {e}", is_error=True)
                _show(case, b.name, out)
                results.append(_tool_result(case, b, out))
            messages.append({"role": "user", "content": results})
        if case.load().get("final"):
            return
    case.emit("log", text=f"وقف بعد {MAX_TURNS} جولة")


def _kind(q: str) -> str:
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", q):
        return "email address"
    if re.fullmatch(r"\+?[\d\s()\-]{7,}", q):
        return "phone number"
    return "name"


def _finish_run(case: Case, what: str) -> None:
    if case.load().get("final"):
        finish(case, "done", "خلص")
    elif case.cancelled():
        finish(case, "stopped", "انوقف بطلبك قبل الجواب")
    else:
        finish(case, "error", "", f"خلص {what} بدون جواب نهائي. جرب نموذج ثاني من الإعدادات.")


def run_person(case: Case) -> None:
    try:
        d = case.load()
        query = (d.get("query") or "").strip()
        text_only = bool(d.get("text_only")) or not case.photo.exists()
        case.update(status="recon", engine=engine_label() if has_ai() else "local")
        if text_only:
            case.emit("stage", stage="recon", text="إدخال نصي: نبحث مباشرة")
            recon_md = ""
        else:
            case.emit("stage", stage="recon", text="الفحص الأولي: بيانات الملف · قراءة النص · بحث عكسي")
            rec = T.recon(case)
            for p, cap in rec.images:
                case.add_evidence(p, cap)
            recon_md = rec.text[:12000]
        if case.cancelled():
            return finish(case, "stopped", "انوقف بطلبك")
        if not has_ai():
            return finish(case, "error", "", "«من هذا الشخص؟» يحتاج مفتاح OpenRouter أو Anthropic: أضفه من الإعدادات")
        case.update(status="analysing")
        case.emit("stage", stage="analysis", text=f"{engine_label()} يبحث ويتحقق")
        bits = ["Who is this person? File one answer with file_person."]
        if query:
            bits.append(f'The user gave: "{query}" — it looks like a {_kind(query)}.')
        if not text_only:
            w, h = T.photo_size(case)
            bits.append(f"A photo is attached ({w}x{h} px; view_photo boxes use these pixels). "
                        "Describe the face and any uniform or badge, and search that with the name.")
        if recon_md:
            bits.append(f"<recon>\n{recon_md}\n</recon>")
        _agent(case, SYSTEM_PERSON, PERSON_TOOLS, "\n\n".join(bits), None if text_only else case.photo, "file_person")
        _finish_run(case, "البحث")
    except Exception as e:
        case.emit("log", text=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-2000:])
        finish(case, "error", "", _friendly(e))


def run_plate(case: Case) -> None:
    try:
        case.update(status="recon", engine=engine_label() if has_ai() else "local")
        case.emit("stage", stage="recon", text="الفحص الأولي: قراءة النص وكشف العناصر")
        rec = T.recon(case)
        for p, cap in rec.images:
            case.add_evidence(p, cap)
        if case.cancelled():
            return finish(case, "stopped", "انوقف بطلبك")
        if not has_ai():
            return finish(case, "error", "", "قراءة اللوحة تحتاج مفتاح OpenRouter أو Anthropic: أضفه من الإعدادات")
        case.update(status="analysing")
        case.emit("stage", stage="analysis", text=f"{engine_label()} يقرأ اللوحة ويتحقق")
        w, h = T.photo_size(case)
        intro = (f"Read the licence plate in this photo ({w}x{h} px; view_photo boxes use these pixels) and report "
                 f"what it supports. Crop the plate before reading it.\n\n<recon>\n{rec.text[:12000]}\n</recon>")
        _agent(case, SYSTEM_PLATE, PLATE_TOOLS, intro, case.photo, "file_plate")
        _finish_run(case, "قراءة اللوحة")
    except Exception as e:
        case.emit("log", text=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-2000:])
        finish(case, "error", "", _friendly(e))
