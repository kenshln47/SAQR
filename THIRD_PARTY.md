# Third-party components

SAQR's own code is proprietary (see LICENSE). Everything below is someone else's.

| Component | Where | Licence | Commercial use |
|---|---|---|---|
| MapLibre GL JS 4.7.1 | `web/vendor/maplibre-gl.js`, `web/vendor/maplibre-gl.css` | BSD-3-Clause (`web/vendor/maplibre-gl.LICENSE.txt`) | Allowed. Keep the notice. Do not use the MapLibre name to endorse SAQR. |
| mapbox-gl-js ≤ 1.13, embedded in MapLibre | same licence file | BSD-3-Clause | Same duty. |
| mapbox-gl-rtl-text (introducing commit names 0.2.3) | `web/vendor/mapbox-gl-rtl-text.js` | BSD-2-Clause plus the ICU notice, both in `web/vendor/mapbox-gl-rtl-text.LICENSE.md` | Allowed. Keep both notices. |
| [GeoInt](https://github.com/marouane53/GeoInt) scripts | not in this repo; default path `%USERPROFILE%\.claude\skills\geoint` | MIT | The scripts may be shipped. Weights they download may not. |
| StreetCLIP `geolocal/StreetCLIP` | downloaded by GeoInt `prior.py`, not in this repo | CC-BY-NC-4.0 | Not allowed in a paid or public SAQR. The model card also marks private-image geolocation as out of scope. Default `recon.py` invocation passes `--skip calib,prior` so the weights are not loaded. `SAQR_ALLOW_NC_MODELS=1` is the private opt-in. |
| GeoCLIP | same `prior.py` step | MIT (weights and gallery noted by GeoInt `references/models.md`) | The step cannot be split from StreetCLIP, so a commercial build skips the whole prior. |
| OWLv2 | GeoInt `detect.py` | Apache-2.0 | Allowed. |
| GeoCalib | GeoInt `calib.py` | Apache-2.0 | Allowed. SAQR already passes `--skip calib`. |
| MegaLoc `gberton/MegaLoc` | GeoInt `sweep.py` | MIT | Allowed. Still only as good as the panorama source it ranks. |
| CARTO Dark Matter GL style | loaded at runtime from `basemaps.cartocdn.com` (`web/app.js`) | not vendored, not yet cleared | Open finding H-NET-01. |
| Esri World Imagery tiles | loaded at runtime from `server.arcgisonline.com` (`web/app.js`) | no key, not cleared | Open finding H-ESRI-01. Not a substitute for a Google key. |
| Inter, IBM Plex Sans Arabic | `fonts.googleapis.com` from `web/index.html` | SIL Open Font License for both families; the Google CSS host is a network call | Fonts may be vendored later. The hotlink is H-NET-01. |

Google Street View, Google satellite tiles, and Apple, Bing, and Yandex panoramas are not bundled. SAQR refuses those calls unless the matching key is set (`SAQR_GOOGLE_KEY` or `GOOGLE_MAPS_API_KEY`, `SAQR_APPLE_KEY`, `SAQR_BING_KEY`, `SAQR_YANDEX_KEY`). The default panorama provider is Mapillary. Keys already in the environment are forwarded to the GeoInt subprocess; the Anthropic and OpenRouter keys are not.
