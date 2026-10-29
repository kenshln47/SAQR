"""Person search is opt-in. A private pin needs a listing tie. Plate owner stays empty."""
from __future__ import annotations

from app.limits import listing_block, person_refusal, person_search_enabled, plate_final, private_final


def test_private_final_stops_at_the_city_without_a_listing_tie() -> None:
    filed = private_final({"level": "point", "radius_km": 0.05, "lat": 24.7, "lon": 46.6, "unverified": []})
    assert filed["level"] == "city"
    assert filed["radius_km"] == 15.0
    assert filed["listing_tie"] is False
    assert any("stops at the city" in item for item in filed["unverified"])


def test_private_final_keeps_a_point_when_a_listing_ties_it() -> None:
    filed = private_final({
        "level": "point", "radius_km": 0.05, "lat": 24.7, "lon": 46.6,
        "listing_tie": True, "unverified": [],
    })
    assert filed["level"] == "point"
    assert filed["radius_km"] == 0.05
    assert filed["listing_tie"] is True


def test_listing_search_is_allowed_for_a_private_place() -> None:
    assert listing_block("private") is None
    assert listing_block("street") is None


def test_plate_owner_is_cleared() -> None:
    assert plate_final({"plate": "1234", "owner": "someone"})["owner"] == ""


def test_person_refusal_does_not_name_anyone() -> None:
    final = person_refusal()
    assert final["found"] is False
    assert final["name"] == ""
    assert final["accounts"] == []


def test_person_search_is_off_unless_the_flag_is_set(monkeypatch) -> None:
    monkeypatch.delenv("SAQR_PERSON_SEARCH", raising=False)
    assert person_search_enabled() is False
    monkeypatch.setenv("SAQR_PERSON_SEARCH", "1")
    assert person_search_enabled() is True
