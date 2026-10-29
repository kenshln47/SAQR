"""Context size as a token estimate. This is not a model tokenizer.

Mixed Arabic and English is charged at 2 characters per token so the budget
is not silently too large. An image part is 1600 tokens, a fixed stand-in.
The provider's own usage numbers, when a response includes them, are stored
separately on the case.
"""
from __future__ import annotations

import os

CHARS_PER_TOKEN = 2
IMAGE_TOKENS = 1600
_IMAGE_TYPES = {"image", "image_url"}
_NOTE = "[older image removed; it is in the case evidence]"


def estimate_text(text: str) -> int:
    if not text:
        return 0
    return (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


def clip_text(text: str, tokens: int) -> str:
    """Keep at most `tokens` of text. Short strings are unchanged."""
    if tokens <= 0 or not text:
        return ""
    limit = tokens * CHARS_PER_TOKEN
    if len(text) <= limit:
        return text
    note = "\n[clipped to the token budget]"
    if len(note) >= limit:
        return text[:limit]
    return text[:limit - len(note)] + note


def _budget(name: str, default: int, floor: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except ValueError:
        value = default
    return max(floor, value)


def context_token_budget() -> int:
    return _budget("SAQR_CONTEXT_TOKENS", 24000, 1000)


def recon_token_budget() -> int:
    return _budget("SAQR_RECON_TOKENS", 8000, 200)


def usage_delta(payload) -> dict[str, int]:
    """Anthropic usage object or an OpenRouter usage dict. Empty when the provider sent nothing."""
    if payload is None:
        return {}
    if isinstance(payload, dict):
        prompt = int(payload.get("prompt_tokens") or payload.get("input_tokens") or 0)
        completion = int(payload.get("completion_tokens") or payload.get("output_tokens") or 0)
    else:
        prompt = int(getattr(payload, "input_tokens", 0) or 0)
        completion = int(getattr(payload, "output_tokens", 0) or 0)
    out: dict[str, int] = {}
    if prompt:
        out["prompt_tokens"] = prompt
    if completion:
        out["completion_tokens"] = completion
    return out


def _parts(content):
    if not isinstance(content, list):
        return
    for part in content:
        if not isinstance(part, dict):
            continue
        yield part
        if part.get("type") == "tool_result" and isinstance(part.get("content"), list):
            yield from _parts(part["content"])


def part_tokens(part: dict) -> int:
    kind = part.get("type")
    if kind in _IMAGE_TYPES:
        return IMAGE_TOKENS
    if kind == "text":
        return estimate_text(str(part.get("text") or ""))
    if kind == "tool_result":
        content = part.get("content")
        if isinstance(content, str):
            return estimate_text(content)
        if isinstance(content, list):
            return sum(part_tokens(item) for item in content if isinstance(item, dict))
    return 0


def message_tokens(messages: list) -> int:
    total = 0
    for message in messages:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str):
            total += estimate_text(content)
        elif isinstance(content, list):
            total += sum(part_tokens(part) for part in content if isinstance(part, dict))
    return total


def _images(messages: list) -> list[dict]:
    found = []
    for message in messages:
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        for part in _parts(message.get("content")):
            if part.get("type") in _IMAGE_TYPES:
                found.append(part)
    return found


def _texts(messages: list) -> list[dict]:
    found = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        for part in _parts(message.get("content")):
            if part.get("type") == "text" and part.get("text"):
                found.append(part)
    return found


def _drop_image(part: dict) -> None:
    part.clear()
    part.update({"type": "text", "text": _NOTE})


def prune_messages(messages: list, budget: int) -> int:
    """Drop oldest images, then shorten oldest text, until the estimate fits. Returns that estimate."""
    if budget < 0:
        budget = 0
    while message_tokens(messages) > budget:
        images = _images(messages)
        if len(images) > 1 or (len(images) == 1 and budget < IMAGE_TOKENS):
            _drop_image(images[0])
            continue
        break
    guard = 0
    while message_tokens(messages) > budget and guard < 40:
        guard += 1
        texts = [part for part in _texts(messages) if estimate_text(str(part.get("text") or "")) > 4]
        if not texts:
            break
        part = max(texts, key=lambda item: estimate_text(str(item.get("text") or "")))
        part["text"] = clip_text(str(part["text"]), max(4, estimate_text(str(part["text"])) // 2))
    return message_tokens(messages)
