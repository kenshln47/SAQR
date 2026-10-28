"""Score a geolocation guess against a known point. No network, no weights.

GeoInt ``scripts/bench.py`` ``metrics`` reports median km, hit rates, and
country accuracy. It does not report ECE, and importing it pulls Street View
code. This module is the scorer the tests run. It does not measure SAQR: a
caller has to pass real rows. Do not fill those rows from ``bench.py
make-streetview`` (keyless Google imagery).
"""
from __future__ import annotations

import math

EARTH_KM = 6371.0088  # same sphere as GeoInt photo_session.haversine_km
CONFIDENCE = {"high": 0.85, "medium": 0.55, "low": 0.25}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * EARTH_KM * math.asin(min(1.0, math.sqrt(a)))


def median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    if n % 2:
        return ordered[n // 2]
    return (ordered[n // 2 - 1] + ordered[n // 2]) / 2


def country_match(true: str | None, pred: str | None) -> bool | None:
    if true is None or pred is None:
        return None
    a, b = str(true).strip().casefold(), str(pred).strip().casefold()
    if not a or not b:
        return None
    return a == b


def confidence_probability(value: object) -> float | None:
    """Map high/medium/low, or a number in [0, 1]. Numbers above 1 are percents."""
    if value is None or value == "":
        return None
    if isinstance(value, str):
        key = value.strip().lower()
        if key in CONFIDENCE:
            return CONFIDENCE[key]
        try:
            value = float(key)
        except ValueError:
            return None
    try:
        p = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(p):
        return None
    if p > 1.0:
        p = p / 100.0
    if p < 0.0 or p > 1.0:
        return None
    return p


def ece(probabilities: list[float], outcomes: list[bool], bins: int = 10) -> float | None:
    """Expected calibration error over equal-width bins on [0, 1].

    Empty bins are skipped. The weight of a bin is its share of the rows.
    """
    if not probabilities or len(probabilities) != len(outcomes) or bins < 1:
        return None
    counts = [0] * bins
    conf_sum = [0.0] * bins
    hit_sum = [0.0] * bins
    for p, outcome in zip(probabilities, outcomes):
        p = min(1.0, max(0.0, float(p)))
        index = min(bins - 1, int(p * bins))
        counts[index] += 1
        conf_sum[index] += p
        hit_sum[index] += 1.0 if outcome else 0.0
    total = sum(counts)
    if not total:
        return None
    error = 0.0
    for index, count in enumerate(counts):
        if not count:
            continue
        error += (count / total) * abs((hit_sum[index] / count) - (conf_sum[index] / count))
    return error


def score(rows: list[dict]) -> dict:
    """rows: error_km, or pred_lat/pred_lon/true_lat/true_lon.

    Optional country_true, country_pred, confidence, radius_km.
    confidence_ece compares the stated confidence with a country hit.
    radius_ece compares it with ``error_km <= radius_km``.
    """
    empty = {"n": 0, "median_km": None, "within_1km": None, "within_25km": None,
             "country_accuracy": None, "confidence_ece": None, "radius_ece": None}
    if not rows:
        return empty
    errors: list[float] = []
    countries: list[bool] = []
    conf_p: list[float] = []
    conf_y: list[bool] = []
    rad_p: list[float] = []
    rad_y: list[bool] = []
    for row in rows:
        if row.get("error_km") is None:
            err = haversine_km(float(row["pred_lat"]), float(row["pred_lon"]),
                               float(row["true_lat"]), float(row["true_lon"]))
        else:
            err = float(row["error_km"])
        errors.append(err)
        match = country_match(row.get("country_true"), row.get("country_pred"))
        if match is not None:
            countries.append(match)
        p = confidence_probability(row.get("confidence"))
        if p is not None and match is not None:
            conf_p.append(p)
            conf_y.append(match)
        if p is not None and row.get("radius_km") is not None:
            rad_p.append(p)
            rad_y.append(err <= float(row["radius_km"]))
    n = len(errors)
    return {
        "n": n,
        "median_km": median(errors),
        "within_1km": sum(e <= 1.0 for e in errors) / n,
        "within_25km": sum(e <= 25.0 for e in errors) / n,
        "country_accuracy": (sum(countries) / len(countries)) if countries else None,
        "confidence_ece": ece(conf_p, conf_y),
        "radius_ece": ece(rad_p, rad_y),
    }
