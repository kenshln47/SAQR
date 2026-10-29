"""B-PRIV-01: private place stops at the city. Person mode does not identify. Plate owner stays empty."""
from __future__ import annotations

from app.limits import listing_block, person_refusal, plate_final, private_final


def test_private_final_stops_at_the_city() -> None:
    filed = private_final({"level": "point", "radius_km": 0.05, "lat": 24.7, "lon": 46.6, "unverified": []})
    assert filed["level"] == "city"
    assert filed["radius_km"] == 15.0
    assert any("not pinned" in item for item in filed["unverified"])


def test_listing_search_is_blocked_for_a_private_place() -> None:
    assert listing_block("private")
    assert listing_block("street") is None


def test_plate_owner_is_cleared() -> None:
    assert plate_final({"plate": "1234", "owner": "someone"})["owner"] == ""


def test_person_refusal_does_not_name_anyone() -> None:
    final = person_refusal()
    assert final["found"] is False
    assert final["name"] == ""
    assert final["accounts"] == []
