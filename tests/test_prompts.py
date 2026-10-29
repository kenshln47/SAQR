"""Plate does not guess an owner. Person found is not a same-name hit. H-PROMPT-01."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = (ROOT / "app/agent.py").read_text(encoding="utf-8")
IDENTIFY = (ROOT / "app/identify.py").read_text(encoding="utf-8")


def _block(text: str, name: str) -> str:
    start = text.index(f"{name} = ")
    opener = text.index('"""', start)
    closer = text.index('"""', opener + 3)
    return text[opener + 3:closer]


def test_plate_prompt_does_not_guess_an_owner() -> None:
    plate = _block(IDENTIFY, "SYSTEM_PLATE")
    assert "Leave owner empty" in plate
    assert "Absher" not in plate
    assert "Mojaz" not in plate
    assert "Do not guess, infer, or search for an owner" in plate


def test_person_prompt_separates_found_from_the_same_name() -> None:
    person = _block(IDENTIFY, "SYSTEM_PERSON")
    assert "found to false" in person
    assert "same name" in person
    assert "gravatar_lookup" in person
    assert "SAQR_PERSON_SEARCH=1" in person
    body = IDENTIFY.split("def run_person", 1)[1].split("def run_plate", 1)[0]
    assert "person_search_enabled" in body
    assert "person_refusal" in body
    assert "_agent(" in body


def test_private_prompt_does_not_point_at_a_missing_rule() -> None:
    private = _block(AGENT, "PRIVATE_NOTE")
    assert "rule above" not in private
    assert "stands alone" in private
    assert "Do not guess, infer, or name an owner" in private
    assert "Do not invent a building" in private
    assert "listing_search" in private
    assert "listing_tie" in private
    assert "only when a listing" in private
    assert "stops at the city" in private
    assert "Do not name a school" in private
    assert "Pin the building" not in private
