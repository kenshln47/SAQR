"""The UI does not call Google Fonts or the CARTO style host. H-NET-01."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_fonts_are_local_and_the_style_is_vendored() -> None:
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    assert "fonts.googleapis.com" not in html
    assert "fonts.css" in html
    assert "basemaps.cartocdn.com" not in js
    assert 'style: "vendor/ofm-dark.json"' in js
    style = json.loads((ROOT / "web/vendor/ofm-dark.json").read_text(encoding="utf-8"))
    assert style["sources"]["openmaptiles"]["url"] == "https://tiles.openfreemap.org/planet"
    assert style["glyphs"].startswith("https://tiles.openfreemap.org/fonts/")
    for weight in (400, 500, 600, 700):
        assert (ROOT / f"web/fonts/inter-latin-{weight}-normal.woff2").stat().st_size > 1000
        assert (ROOT / f"web/fonts/ibm-plex-sans-arabic-arabic-{weight}-normal.woff2").stat().st_size > 1000
    assert "SIL Open Font License" in (ROOT / "web/fonts/inter.OFL.txt").read_text(encoding="utf-8")
    assert "SIL Open Font License" in (ROOT / "web/fonts/ibm-plex.OFL.txt").read_text(encoding="utf-8")
    lic = (ROOT / "web/vendor/ofm-dark.LICENSE.txt").read_text(encoding="utf-8")
    assert "BSD 3-Clause" in lic and "CC-BY 4.0" in lic


def test_satellite_toggle_is_esri_world_imagery() -> None:
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    assert "server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" in js
    assert "maxzoom: 19" in js
    assert "Esri, Maxar, Earthstar Geographics, and the GIS User Community" in js
    assert "gibs.earthdata.nasa.gov" not in js
    assert "map.setMaxZoom(19)" in js

