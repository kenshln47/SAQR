# Decisions

ADR-001. Proprietary, not MIT: the code stays sellable, and read-only adoption (fork, self-host, or republish) is blocked unless a separate grant is given.

ADR-002. A commercial process passes `recon.py --skip calib,prior`. GeoInt's `--skip` is one comma-separated value, so that flag alone also skips GeoCLIP. `SAQR_ALLOW_NC_MODELS=1` restores the old `calib`-only skip for a private non-commercial install. The commercial recovery is ADR-004, not leaving GeoCLIP off.

ADR-003. The default panorama provider is Mapillary, not Google. Kartaview and Panoramax stay selectable with no key. Google, Apple, Bing, and Yandex each require their own environment variable. One Google key does not unlock the other three. `streetview_near` and `streetview_views` call `gsv.py` and stay dark until a Google key is present.

ADR-004. Commercial runs still pass `--skip prior` so StreetCLIP is not loaded, then call `prior.py --models geoclip` into `recon/prior`. The numeric gap versus StreetCLIP is unmeasured. H-GEOCLIP-01 stays open until that score exists.
