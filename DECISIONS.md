# Decisions

ADR-001. SAQR's own code is proprietary (all rights reserved), not MIT or Apache. The product is sold. The permissive licences of MapLibre, rtl-text, and the GeoInt scripts stay intact in NOTICE and THIRD_PARTY.md.

ADR-002. A commercial process passes `recon.py --skip calib,prior`. GeoInt's `--skip` is one comma-separated value. `prior.py` loads StreetCLIP (CC-BY-NC-4.0) and GeoCLIP (MIT) together, so the MIT model is skipped as well. `SAQR_ALLOW_NC_MODELS=1` restores the old `calib`-only skip for a private non-commercial install.

ADR-003. The default panorama provider is Mapillary, not Google. Kartaview and Panoramax stay selectable with no key. Google, Apple, Bing, and Yandex each require their own environment variable. One Google key does not unlock the other three. `streetview_near` and `streetview_views` call `gsv.py` and stay dark until a Google key is present.
