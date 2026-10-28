"""Image verification (manipulation / AI-generation signals) and vehicle identification."""
from __future__ import annotations

import io
import json
import traceback
from typing import List, Literal

import anthropic
from PIL import Image, ImageChops, ImageEnhance
from pydantic import BaseModel

from . import openrouter as OR
from . import tools as T
from .cases import Case
from .config import engine_label, has_ai, model_name, provider
from .agent import _friendly, finish


class Signal(BaseModel):
    name: str
    finding: str
    weight: Literal["supports_genuine", "suggests_manipulation", "suggests_ai", "neutral"]


class Verdict(BaseModel):
    assessment: Literal["likely_genuine", "possibly_manipulated", "likely_manipulated", "possibly_ai_generated",
                        "likely_ai_generated", "inconclusive"]
    ai_generation_likelihood: float
    manipulation_likelihood: float
    signals: List[Signal]
    summary_ar: str
    limits_ar: str


class Vehicle(BaseModel):
    make: str
    model: str
    year_range: str
    body_type: str
    confidence: float
    cues: List[str]
    alternatives: List[str]
    summary_ar: str


def ela(case: Case, quality: int = 90) -> T.ToolOut:
    """Error level analysis: resave at a known JPEG quality and amplify the difference."""
    im = T.upright(case.photo)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality)
    diff = ImageChops.difference(im, Image.open(buf))
    extrema = max(hi for _, hi in diff.getextrema()) or 1
    out = ImageEnhance.Brightness(diff).enhance(255.0 / extrema)
    path = case.dir / "work" / "ela.jpg"
    path.parent.mkdir(exist_ok=True)
    out.save(path, quality=92)
    return T.ToolOut(f"ELA at q{quality}, max difference {extrema}", [(path, "Error level analysis (bright = recompressed differently)")])


def metadata(case: Case) -> str:
    rc, out = T.run_script(case, "meta.py", [str(case.photo), "--out-dir", "meta"], use_uv=True, timeout=300)
    md = case.dir / "work" / "meta" / "meta.md"
    return md.read_text(encoding="utf-8") if md.exists() else f"metadata step failed: {out[-800:]}"


def _parse_openrouter(prompt: str, images: list, schema):
    model = model_name()
    sp = (OR.catalog().get(model) or {}).get("supported_parameters") or []
    body = dict(model=model, max_tokens=16000, **OR.reasoning(model, "high"),
                messages=[{"role": "user", "content": [*[OR.image_part(i) for i in images], {"type": "text", "text": prompt}]}])
    if "structured_outputs" in sp or "response_format" in sp:
        body.update(provider={"require_parameters": True}, response_format={"type": "json_schema", "json_schema": {
            "name": schema.__name__, "strict": True, "schema": OR.strict_schema(schema.model_json_schema())}})
    else:   # models without structured outputs still work: ask for the JSON in words and validate it here
        body["messages"][0]["content"][-1]["text"] += (
            "\n\nReply with one JSON object only, no prose, matching this JSON schema:\n"
            + json.dumps(OR.strict_schema(schema.model_json_schema()), ensure_ascii=False))
    resp = OR.chat(**body)
    choice = (resp.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    if choice.get("finish_reason") == "content_filter" or msg.get("refusal"):
        raise RuntimeError("النموذج رفض يكمل هالطلب")
    if choice.get("finish_reason") == "length":
        raise RuntimeError("رد النموذج انقطع قبل ما يكمل: جرب نموذج ثاني")
    text = msg.get("content") or ""
    return schema.model_validate_json(text[text.find("{"):text.rfind("}") + 1] or text)


def _parse(prompt: str, images: list, schema):
    if provider() == "openrouter":
        return _parse_openrouter(prompt, images, schema)
    client = anthropic.Anthropic()
    resp = client.messages.parse(
        model=model_name(), max_tokens=16000, output_config={"effort": "high"},
        messages=[{"role": "user", "content": [*images, {"type": "text", "text": prompt}]}],
        output_format=schema,
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("النموذج رفض يكمل هالطلب")
    if resp.stop_reason == "max_tokens" or resp.parsed_output is None:
        raise RuntimeError("رد النموذج انقطع قبل ما يكمل: أعد المحاولة")
    return resp.parsed_output


def _done(case: Case, final: dict) -> None:
    case.update(final=final)
    case.emit("final", final=final)
    finish(case, "done", "خلص")


def _failed(case: Case, ex: Exception) -> None:
    case.emit("log", text=f"{type(ex).__name__}: {ex}", trace=traceback.format_exc()[-2000:])
    finish(case, "error", "", _friendly(ex))


def run_verify(case: Case) -> None:
    try:
        case.update(status="analysing", engine=engine_label() if has_ai() else "local")
        case.emit("stage", stage="verify", text="بيانات الملف وتحليل مستوى الخطأ (ELA)")
        meta = metadata(case)
        e = ela(case)
        for p, cap in e.images:
            case.add_evidence(p, cap)
        case.emit("log", text=meta[:1500])
        if not has_ai():
            final = {"assessment": "inconclusive", "summary_ar": "وضع محلي: هذي البيانات الوصفية وصورة ELA بس، بدون قراءة الذكاء الاصطناعي.",
                     "metadata": meta[:3000]}
        else:
            case.emit("stage", stage="analysis", text=f"{engine_label()} يقرأ المؤشرات")
            v = _parse(
                "Assess whether this image is authentic, manipulated or AI-generated. Image 1 is the photo, image 2 its "
                "error level analysis. Consider: provenance hints in the metadata, lighting and shadow consistency, "
                "perspective, text rendering, hands/faces/repeating textures, clone areas, JPEG history, C2PA. "
                "Give signals, not a verdict you cannot support; detectors are fallible. Write summary_ar and limits_ar "
                f"in Gulf Arabic.\n\n<metadata>\n{meta[:6000]}\n</metadata>",
                [T.image_block(case.photo), T.image_block(e.images[0][0])], Verdict)
            final = {**v.model_dump(), "metadata": meta[:3000]}
        _done(case, final)
    except Exception as ex:
        _failed(case, ex)


def run_car(case: Case) -> None:
    try:
        case.update(status="analysing", engine=engine_label() if has_ai() else "local")
        if not has_ai():
            raise RuntimeError("تحديد السيارة يحتاج مفتاح OpenRouter أو Anthropic: أضفه من الإعدادات")
        case.emit("stage", stage="analysis", text=f"{engine_label()} يحدد السيارة")
        v = _parse(
            "Identify the main vehicle in this photo: make, model, generation as a year range, body type. Use grille, "
            "lamps, mirrors, pillars, wheels, badges, dashboard and steering wheel for interiors. Give your cues and the "
            "closest look-alikes. Do not read out or use the licence plate. Write summary_ar in Gulf Arabic.",
            [T.image_block(case.photo)], Vehicle)
        _done(case, v.model_dump())
    except Exception as ex:
        _failed(case, ex)
