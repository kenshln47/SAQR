"""Defaults and the opt-in paths for person search and a private-place pin.

The default does not search for a person and does not keep a building pin.
SAQR_PERSON_SEARCH=1 restores the person loop. A private-place point is kept
only when the filed answer says a listing tied the building.
"""
from __future__ import annotations

import os

CITY_RADIUS_KM = 15.0


def person_search_enabled() -> bool:
    """The person loop runs only when the operator set this. Default is off."""
    return os.environ.get("SAQR_PERSON_SEARCH", "").strip().lower() in {"1", "true", "yes", "on"}


def private_final(inp: dict) -> dict:
    """Keep a point only when listing_tie is true. Otherwise stop at the city."""
    out = dict(inp)
    if out.get("listing_tie") is True and out.get("level") == "point":
        note = "Building pin kept because a listing tied the photo to the building."
        extra = list(out.get("unverified") or [])
        if note not in extra:
            extra.append(note)
        out["unverified"] = extra
        return out
    out["level"] = "city"
    out["listing_tie"] = False
    try:
        radius = float(out.get("radius_km") or 0)
    except (TypeError, ValueError):
        radius = 0.0
    if radius < CITY_RADIUS_KM:
        out["radius_km"] = CITY_RADIUS_KM
    note = "No listing tie. Private-place mode stops at the city. A school and a routine are not named."
    extra = list(out.get("unverified") or [])
    if note not in extra:
        extra.append(note)
    out["unverified"] = extra
    return out


def listing_block(mode: str | None) -> str | None:
    """Listing search is allowed in private mode. The pin still needs listing_tie."""
    return None


def plate_final(inp: dict) -> dict:
    """The plate may be read. The owner field is always empty."""
    out = dict(inp)
    out["owner"] = ""
    return out


def person_refusal() -> dict:
    """Default person result. SAQR_PERSON_SEARCH=1 does not use this."""
    return {
        "found": False,
        "name": "",
        "role": "",
        "accounts": [],
        "confidence": "low",
        "summary": "صقر لا يطابق صورة أو إيميل أو جوال أو اسم بشخص. نفس الاسم ليس نتيجة. البحث عن شخص يحتاج SAQR_PERSON_SEARCH=1.",
        "unverified": ["person identification is not run"],
    }
