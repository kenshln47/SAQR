"""Phase 6 report: the Raven gap file names every required page and a status."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PAGES = (
    "find-region",
    "find-street",
    "find-property",
    "short-term-rental",
    "live-intelligence",
    "identify-car",
    "verify-image",
    "FAQ",
)


def test_gap_names_every_raven_page_and_a_status() -> None:
    gap = (ROOT / "GAP.md").read_text(encoding="utf-8")
    for name in PAGES:
        assert name in gap
    for status in ("HAVE", "PARTIAL", "MISSING"):
        assert status in gap
    assert "short-term-rental-id" in gap
    assert "60" in gap
    assert "estimate" in gap.lower()
    assert "not a measured plan" in gap.lower()
