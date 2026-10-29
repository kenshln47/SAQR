"""Hard stops for private-place, person, and plate-owner results.

These functions refuse. They do not search, and they do not rank a person.
"""
from __future__ import annotations

CITY_RADIUS_KM = 15.0


def private_final(inp: dict) -> dict:
    """A private home, school, or routine stops at the city. No door, no routine pin."""
    out = dict(inp)
    out["level"] = "city"
    try:
        radius = float(out.get("radius_km") or 0)
    except (TypeError, ValueError):
        radius = 0.0
    if radius < CITY_RADIUS_KM:
        out["radius_km"] = CITY_RADIUS_KM
    note = "Private-place mode stops at the city. A building, a school, and a routine are not pinned."
    extra = list(out.get("unverified") or [])
    if note not in extra:
        extra.append(note)
    out["unverified"] = extra
    return out


def listing_block(mode: str | None) -> str | None:
    if mode == "private":
        return "listing search is not used for a private home, a school, or a routine."
    return None


def plate_final(inp: dict) -> dict:
    """The plate may be read. The owner field is always empty."""
    out = dict(inp)
    out["owner"] = ""
    return out


def person_refusal() -> dict:
    """No photo, email, phone, or name is matched to a person."""
    return {
        "found": False,
        "name": "",
        "role": "",
        "accounts": [],
        "confidence": "low",
        "summary": "صقر لا يطابق صورة أو إيميل أو جوال أو اسم بشخص. نفس الاسم ليس نتيجة.",
        "unverified": ["person identification is not run"],
    }
