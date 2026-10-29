"""OpenRouter: one key for models from every lab, through its OpenAI-compatible chat completions API."""
from __future__ import annotations

import os
import threading
import time

import requests

BASE = "https://openrouter.ai/api/v1"
HEADERS = {"HTTP-Referer": "http://127.0.0.1:8765", "X-Title": "SAQR"}

# Ranked by GeoGuessBench v2 (2026-10-06): 210 street photos, one guess each at medium effort.
# It measures the eye, not tool use; SAQR's prompts and tools were tuned on Claude.
RECOMMENDED = [
    {"id": "anthropic/claude-opus-5.5", "label": "Claude Opus 5.5", "tag": "الأفضل",
     "note": "الأول بالاختبار · وسيط الخطأ 10.9 كم · الدولة صح 86%"},
    {"id": "anthropic/claude-fable-5.1", "label": "Claude Fable 5.1", "tag": "",
     "note": "متعادل مع الأول · 8.7 كم · سعره ضعفين ونص"},
    {"id": "meta/muse-glimmer-30b", "label": "Muse Glimmer 30B", "tag": "الأرخص",
     "note": "الثالث · 49.9 كم · الدولة صح 78% · مفتوح المصدر"},
    {"id": "openai/gpt-6-astra", "label": "GPT-6 Astra", "tag": "",
     "note": "الرابع · 21.6 كم · الدولة صح 77% · غالي"},
    {"id": "openai/gpt-6.1-sol", "label": "GPT-6.1 Sol", "tag": "",
     "note": "الخامس · 37.8 كم · الدولة صح 75%"},
    {"id": "z-ai/glm-5.3-flash", "label": "GLM-5.3 Flash", "tag": "",
     "note": "السادس · 61.7 كم · الدولة صح 75% · رخيص"},
    {"id": "google/gemini-4-argon", "label": "Gemini 4 Argon", "tag": "",
     "note": "جديد (13 أكتوبر) · ما انقاس بالاختبار بعد"},
]

_cat: dict = {"at": 0.0, "models": {}}
_lock = threading.Lock()


def catalog() -> dict[str, dict]:
    """Public model list (no key needed), cached for an hour. The lock is not held during the request.

    A failed refresh keeps the previous list. With no list at all, the error propagates so Settings can say so.
    """
    with _lock:
        fresh = time.time() - _cat["at"] <= 3600 and bool(_cat["models"])
        cached = _cat["models"]
    if fresh:
        return cached
    try:
        r = requests.get(f"{BASE}/models", headers=HEADERS, timeout=30)
        r.raise_for_status()
        models = {m["id"]: m for m in r.json().get("data", [])}
    except requests.RequestException:
        with _lock:
            if _cat["models"]:
                return _cat["models"]
        raise
    with _lock:
        _cat["models"] = models
        _cat["at"] = time.time()
        return _cat["models"]


def fits(m: dict) -> bool:
    """SAQR needs a model that sees images and calls tools."""
    return "image" in (m.get("architecture") or {}).get("input_modalities", []) and "tools" in (m.get("supported_parameters") or [])


def usable(model_id: str) -> str | None:
    """None when the model can run SAQR, else the reason in Arabic."""
    m = catalog().get(model_id)
    if not m:
        return f"ما فيه نموذج اسمه {model_id} في OpenRouter"
    if not fits(m):
        return f"{model_id} ما يقبل صور أو ما يدعم الأدوات، وصقر يحتاج الاثنين"
    return None


def price(m: dict) -> dict:
    p = m.get("pricing") or {}
    return {"in": round(float(p.get("prompt", 0)) * 1e6, 2), "out": round(float(p.get("completion", 0)) * 1e6, 2)}


def check_key(key: str) -> dict:
    r = requests.get(f"{BASE}/key", headers={**HEADERS, "Authorization": f"Bearer {key}"}, timeout=20)
    if r.status_code == 401:
        raise PermissionError("OpenRouter رفض المفتاح: تأكد إنك نسخته كامل وإنه مو ملغي")
    r.raise_for_status()
    return r.json().get("data", {})


def chat(**body) -> dict:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    for attempt in range(3):
        try:
            r = requests.post(f"{BASE}/chat/completions", json=body, timeout=900,
                              headers={**HEADERS, "Authorization": f"Bearer {key}"})
        except requests.ConnectionError:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code in (408, 429, 500, 502, 503, 504) and attempt < 2:
            time.sleep(5 * (attempt + 1))
            continue
        try:
            data = r.json()
        except ValueError:
            data = {}
        choice_err = ((data.get("choices") or [{}])[0] or {}).get("error") if isinstance(data, dict) else None
        if r.status_code >= 400 or not isinstance(data, dict) or "error" in data or choice_err or not data.get("choices"):
            err = (data.get("error") if isinstance(data, dict) else None) or choice_err or {}
            raise RuntimeError(f"OpenRouter {err.get('code', r.status_code)}: {err.get('message', r.text[:300])}")
        return data
    raise RuntimeError("OpenRouter busy, try again")


def reasoning(model_id: str, effort: str) -> dict:
    """Ask for thinking only where the model supports it. If the model list is down, skip the parameter."""
    try:
        models = catalog()
    except requests.RequestException:
        return {}
    m = models.get(model_id) or {}
    return {"reasoning": {"effort": effort}} if "reasoning" in (m.get("supported_parameters") or []) else {}


def image_part(block: dict) -> dict:
    """Anthropic base64 image block -> OpenAI-style image_url part."""
    src = block["source"]
    return {"type": "image_url", "image_url": {"url": f"data:{src['media_type']};base64,{src['data']}"}}


def function_tools(tools: list[dict]) -> list[dict]:
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                              "parameters": t["input_schema"]}} for t in tools]


def strict_schema(s):
    """Pydantic JSON schema -> strict structured-output schema (closed objects, every field required)."""
    if isinstance(s, dict):
        s = {k: strict_schema(v) for k, v in s.items()}
        if s.get("type") == "object" and "properties" in s:
            s["additionalProperties"] = False
            s["required"] = list(s["properties"])
        return s
    if isinstance(s, list):
        return [strict_schema(v) for v in s]
    return s
