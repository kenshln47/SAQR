# Decisions

ADR-001. Proprietary, not MIT: the code stays sellable, and read-only adoption (fork, self-host, or republish) is blocked unless a separate grant is given.

ADR-002. A commercial process passes `recon.py --skip calib,prior`. GeoInt's `--skip` is one comma-separated value, so that flag alone also skips GeoCLIP. `SAQR_ALLOW_NC_MODELS=1` restores the old `calib`-only skip for a private non-commercial install. The commercial recovery is ADR-004, not leaving GeoCLIP off.

ADR-003. The default panorama provider is Mapillary, not Google. Kartaview and Panoramax stay selectable with no key. Google, Apple, Bing, and Yandex each require their own environment variable. One Google key does not unlock the other three. `streetview_near` and `streetview_views` call `gsv.py` and stay dark until a Google key is present.

ADR-004. Commercial runs still pass `--skip prior` so StreetCLIP is not loaded, then call `prior.py --models geoclip` into `recon/prior`. The numeric gap versus StreetCLIP is unmeasured. H-GEOCLIP-01 stays open until that score exists.

ADR-005. At most `SAQR_WORKERS` analyses run at once (default 2, hard cap 8). The upload returns immediately; the extra job waits for a slot before it starts a subprocess.

ADR-006. Context is a token budget, not "6 images" or a 20000-character cut. The estimate is 2 characters per token and 1600 tokens per image. Defaults: `SAQR_CONTEXT_TOKENS=24000`, `SAQR_RECON_TOKENS=8000`. Provider usage is recorded when the response includes it.

ADR-007. Docker keeps the 127.0.0.1 bind. Host networking is the way out of the container. Binding 0.0.0.0 is rejected.

ADR-008. Setup clones https://github.com/marouane53/GeoInt.git when `scripts/recon.py` is missing. The skill stays outside this repo. An existing install is not overwritten.

ADR-009. The map style is the OpenFreeMap build of dark-matter, stored in the repo, not fetched from `basemaps.cartocdn.com`. Tiles stay on `tiles.openfreemap.org`. Their own page says commercial use is allowed. Fonts are the SIL OFL files in `web/fonts/`, not `fonts.googleapis.com`.

