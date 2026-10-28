"""Gates in app.licensing. No network, no geoint, no images."""
from __future__ import annotations

import pytest

from app.licensing import (
    DEFAULT_PANO,
    nc_models_allowed,
    normalise_pano,
    pano_block_reason,
    prior_followup_args,
    recon_skip_arg,
    satellite_block_reason,
)


def test_prior_is_skipped_unless_opted_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SAQR_ALLOW_NC_MODELS", raising=False)
    assert nc_models_allowed() is False
    assert recon_skip_arg() == "calib,prior"


@pytest.mark.parametrize("value", ["1", "true", "yes", "on", "TRUE"])
def test_nc_opt_in(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("SAQR_ALLOW_NC_MODELS", value)
    assert nc_models_allowed() is True
    assert recon_skip_arg() == "calib"


def test_blank_opt_in_does_not_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAQR_ALLOW_NC_MODELS", "  ")
    assert nc_models_allowed() is False


def test_commercial_followup_is_geoclip_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SAQR_ALLOW_NC_MODELS", raising=False)
    args = prior_followup_args("/tmp/photo.jpg")
    assert args == ["/tmp/photo.jpg", "--out-dir", "recon/prior", "--models", "geoclip"]
    assert args is not None and "streetclip" not in args


def test_nc_opt_in_skips_the_geoclip_followup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAQR_ALLOW_NC_MODELS", "1")
    assert prior_followup_args("/tmp/photo.jpg") is None


def test_default_panorama_is_mapillary() -> None:
    assert DEFAULT_PANO == "mapillary"
    assert normalise_pano(None) == "mapillary"
    assert normalise_pano("  ") == "mapillary"
    assert normalise_pano(" Google ") == "google"


def test_closed_panoramas_need_their_own_key(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("SAQR_GOOGLE_KEY", "GOOGLE_MAPS_API_KEY", "SAQR_APPLE_KEY", "SAQR_BING_KEY", "SAQR_YANDEX_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert pano_block_reason("mapillary") is None
    assert pano_block_reason("kartaview") is None
    assert pano_block_reason("panoramax") is None
    assert "SAQR_GOOGLE_KEY" in (pano_block_reason("google") or "")
    assert pano_block_reason("apple")
    assert pano_block_reason("bing")
    assert pano_block_reason("yandex")
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "paid-key")
    assert pano_block_reason("google") is None
    assert pano_block_reason("apple")  # a Google key does not unlock Apple


def test_google_satellite_is_keyed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SAQR_GOOGLE_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    assert satellite_block_reason("esri")
    assert satellite_block_reason("wayback:2020-01")
    assert satellite_block_reason("bing") is None
    assert satellite_block_reason("google")
    assert satellite_block_reason("google-hybrid")
    monkeypatch.setenv("SAQR_GOOGLE_KEY", "paid-key")
    assert satellite_block_reason("google-hybrid") is None
    assert satellite_block_reason("esri")
