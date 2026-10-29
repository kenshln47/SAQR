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

ADR-010. The satellite toggle was NASA GIBS Blue Marble Next Generation, matrix `GoogleMapsCompatible_Level8`. Sentinel-2 cloudless on s2maps.eu is non-commercial for 2018–2024 and was not used. That choice is superseded for the live imagery layer by ADR-011. Google satellite still needs its own key. Bing is unchanged.

ADR-011. Esri World Imagery is the satellite layer again, on the map and as the agent tool default. Zoom is 3–19. Attribution is "Esri, Maxar, Earthstar Geographics, and the GIS User Community". Wayback stays refused. This is a gate (named source, zoom cap, attribution), not a deletion and not an unscoped Esri archive.

ADR-012. If `tiles.openfreemap.org` fails or rate-limits, the map stops and the rest of SAQR keeps running. There is no automatic second free tile host. The replacement is explicit: edit `web/vendor/ofm-dark.json` so its sources point at a paid vector-tile endpoint or at a self-hosted OpenMapTiles/Planetiler or Protomaps server. Paid is the path when the operator will not run a tile server. Self-host is the path when tiles must not leave the machine. Neither is downloaded by setup.

ADR-013. Bing satellite needs `SAQR_BING_KEY`, same rule as Bing panoramas. A Google key does not unlock it. Wayback (`wayback:YYYY`) is still refused. It was not restored when Esri World Imagery came back. It is a different archive and this build does not call it.

ADR-014. `scripts/setup.sh` and `setup.bat` use the same torch rule. The default index is `https://download.pytorch.org/whl/cpu`. Both switch to `https://download.pytorch.org/whl/cu130` only when `nvidia-smi -L` succeeds. `streetlevel` stays `--no-deps`. Importing `streetlevel` itself does not need `pyexiv2`. Importing `streetlevel.streetview` (also baidu, yandex, naver, kakao) does, because those modules import `streetlevel.exif`, and that file imports `pyexiv2` at load time. A round trip on this machine wrote GPS `24.7136, 46.6753` with `save_with_metadata` and read `Exif.GPSInfo.GPSLatitude` / `GPSLongitude` back through `pyexiv2` 2.16.0. `pyexiv2==2.16.0` is in `requirements.txt` and in the lock. `pytest`, `pytest-asyncio`, and `cython` are still not installed: those modules do not import them. `streetlevel.mapy` imports `pyfrpc`, which does not build on Windows and is not a provider SAQR calls, so it stays out.


