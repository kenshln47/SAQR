"""Scoring math only. No photos, no GeoInt, no claimed SAQR accuracy."""
from __future__ import annotations

import math

from app.benchscore import EARTH_KM, ece, haversine_km, score


def test_haversine_matches_the_photo_session_sphere() -> None:
    degree = EARTH_KM * math.pi / 180
    assert haversine_km(0, 0, 0, 0) == 0
    assert abs(haversine_km(0, 0, 1, 0) - degree) < 1e-6
    assert abs(haversine_km(24.7136, 46.6753, 24.7136, 46.6753)) < 1e-9


def test_score_median_hits_and_country() -> None:
    degree = EARTH_KM * math.pi / 180
    rows = [
        {"pred_lat": 0, "pred_lon": 0, "true_lat": 0, "true_lon": 0,
         "country_true": "SA", "country_pred": "sa", "confidence": "high", "radius_km": 1},
        {"error_km": degree, "country_true": "SA", "country_pred": "YE",
         "confidence": "low", "radius_km": 25},
    ]
    got = score(rows)
    assert got["n"] == 2
    assert abs(got["median_km"] - degree / 2) < 1e-6
    assert got["within_1km"] == 0.5
    assert got["within_25km"] == 0.5
    assert got["country_accuracy"] == 0.5
    # high 0.85 vs hit, low 0.25 vs miss → (0.15 + 0.25) / 2
    assert got["confidence_ece"] is not None and abs(got["confidence_ece"] - 0.2) < 1e-9
    # radius: 0 km <= 1 (hit at 0.85), degree km <= 25 (miss at 0.25)
    assert got["radius_ece"] is not None and abs(got["radius_ece"] - 0.2) < 1e-9


def test_ece_bins() -> None:
    assert ece([0.85, 0.25], [True, False]) == 0.2
    assert ece([], []) is None
    assert score([])["median_km"] is None
    assert score([{"error_km": 3.0}])["country_accuracy"] is None
