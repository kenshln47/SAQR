"""Commercial gates: non-commercial weights and closed-platform imagery.

GeoInt's prior step loads StreetCLIP (CC-BY-NC-4.0) and GeoCLIP (MIT) together.
recon.py --skip is one comma-separated string, not a repeatable flag
(scripts/recon.py: add_argument("--skip", default="")). A commercial run
skips that step, then calls prior.py --models geoclip on its own.
"""
from __future__ import annotations

import os

DEFAULT_PANO = "mapillary"
OPEN_PANO = ("mapillary", "kartaview", "panoramax")
# A Google key does not license Apple, Bing, or Yandex imagery.
CLOSED_PANO = {
    "google": ("SAQR_GOOGLE_KEY", "GOOGLE_MAPS_API_KEY"),
    "apple": ("SAQR_APPLE_KEY",),
    "bing": ("SAQR_BING_KEY",),
    "yandex": ("SAQR_YANDEX_KEY",),
}
_TRUTHY = {"1", "true", "yes", "on"}


def nc_models_allowed() -> bool:
    """StreetCLIP is off unless the operator opts in. Not for a paid build."""
    return os.environ.get("SAQR_ALLOW_NC_MODELS", "").strip().lower() in _TRUTHY


def recon_skip_arg() -> str:
    """Value of recon.py --skip. calib is always skipped; prior is skipped commercially."""
    parts = ["calib"]
    if not nc_models_allowed():
        parts.append("prior")
    return ",".join(parts)


def prior_followup_args(photo: str) -> list[str] | None:
    """Argv for a GeoCLIP-only prior.py call after recon.py.

    None when the non-commercial opt-in already runs StreetCLIP and GeoCLIP
    inside recon.py. The commercial path must not pass --models streetclip.
    """
    if nc_models_allowed():
        return None
    return [photo, "--out-dir", "recon/prior", "--models", "geoclip"]


def normalise_pano(provider: str | None) -> str:
    text = (provider or "").strip().lower()
    return text or DEFAULT_PANO


def _key_set(names: tuple[str, ...]) -> bool:
    return any(os.environ.get(name, "").strip() for name in names)


def pano_block_reason(provider: str | None) -> str | None:
    """None when this panorama provider may be called."""
    name = normalise_pano(provider)
    needed = CLOSED_PANO.get(name)
    if not needed:
        return None
    if _key_set(needed):
        return None
    keys = " or ".join(needed)
    return (
        f"{name} panoramas need {keys}. "
        "Use mapillary, kartaview, or panoramax, which do not require that key."
    )


def satellite_block_reason(source: str | None) -> str | None:
    """None when this satellite source may be called.

    esri is World Imagery, zoom 3–19, with the Esri attribution on the map and in the tool text.
    Wayback (wayback:YYYY) is still refused. It was not restored. It is a different Esri archive,
    not the live World Imagery layer.
    google and google-hybrid need a Google key. bing needs SAQR_BING_KEY. A Google key does not unlock Bing.
    """
    name = (source or "").strip().lower()
    if name.startswith("wayback:"):
        return (
            f"{name} tiles are not called. Wayback is still refused. It was not restored. "
            "It is not the live World Imagery layer. "
            "Use esri, or google or google-hybrid with a Google key, or bing with SAQR_BING_KEY."
        )
    if name == "bing":
        if _key_set(("SAQR_BING_KEY",)):
            return None
        return (
            "bing tiles need SAQR_BING_KEY. A Google key does not unlock Bing. "
            "esri World Imagery does not need that key. Wayback is still refused and was not restored."
        )
    if name not in {"google", "google-hybrid"}:
        return None
    if _key_set(CLOSED_PANO["google"]):
        return None
    return (
        f"{name} tiles need SAQR_GOOGLE_KEY or GOOGLE_MAPS_API_KEY. "
        "esri World Imagery does not need that key. bing needs SAQR_BING_KEY. "
        "Wayback is still refused and was not restored."
    )
