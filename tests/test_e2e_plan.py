"""The end-to-end scorer shape. No network, no model, no invented rows."""
from __future__ import annotations

import io

from PIL import Image

from bench.e2e import CONFIGS, aggregate, strip_exif
import bench.run_e2e as run_e2e


def test_four_configurations() -> None:
    ids = [c["id"] for c in CONFIGS]
    assert ids == ["prior_rev", "prior_norev", "skip_prior_rev", "skip_prior_norev"]
    assert sum(1 for c in CONFIGS if c["nc_models"]) == 2
    assert sum(1 for c in CONFIGS if c["rev"]) == 2


def test_aggregate_is_per_config_and_per_stratum() -> None:
    detail = [
        {"config": "prior_rev", "stratum": "city", "pred_lat": 48.0, "pred_lon": 2.0,
         "true_lat": 48.01, "true_lon": 2.01, "country_true": "FR", "country_pred": "FR",
         "confidence": "high", "radius_km": 5},
        {"config": "prior_rev", "stratum": "rural", "pred_lat": 0.0, "pred_lon": 0.0,
         "true_lat": 10.0, "true_lon": 10.0, "country_true": "FR", "country_pred": "US",
         "confidence": "low", "radius_km": 1},
        {"config": "skip_prior_rev", "stratum": "city", "id": "x", "error": "no final"},
    ]
    out = aggregate(detail)
    city = out["configs"]["prior_rev"]["by_stratum"]["city"]
    rural = out["configs"]["prior_rev"]["by_stratum"]["rural"]
    assert city["n"] == 1 and rural["n"] == 1
    assert city["median_km"] < rural["median_km"]
    assert out["configs"]["skip_prior_rev"]["n_scored"] == 0
    assert out["configs"]["skip_prior_rev"]["n_detail"] == 1
    assert "GeoCLIP-only" in out["what"]


def test_strip_exif_drops_the_description_tag() -> None:
    im = Image.new("RGB", (4, 4), "red")
    exif = Image.Exif()
    exif[0x010E] = "device location"
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=exif)
    cleaned = Image.open(io.BytesIO(strip_exif(buf.getvalue())))
    assert not cleaned.getexif().get(0x010E)


def test_no_key_does_not_write_a_score(monkeypatch) -> None:
    monkeypatch.setattr(run_e2e, "has_ai", lambda: False)
    assert run_e2e.main() == 2
