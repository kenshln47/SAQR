"""CSP names the hosts the page still calls, and still refuses framing. L-CSP-01."""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("SAQR_CASES", tempfile.mkdtemp(prefix="saqr-csp-"))

from app.server import CONTENT_SECURITY_POLICY


def test_csp_allows_the_map_and_blocks_framing() -> None:
    policy = CONTENT_SECURITY_POLICY
    assert "frame-ancestors 'none'" in policy
    assert "worker-src 'self' blob:" in policy
    assert "https://tiles.openfreemap.org" in policy
    assert "https://server.arcgisonline.com" in policy
    assert "https://nominatim.openstreetmap.org" in policy
    assert "gibs.earthdata.nasa.gov" not in policy
    assert "basemaps.cartocdn.com" not in policy
    assert "fonts.googleapis.com" not in policy
    assert "default-src 'self'" in policy
