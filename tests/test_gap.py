"""Phase 6 report: the Raven gap file, and a README that matches the code."""
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


def test_readme_states_the_city_stop_and_does_not_rank_a_winner() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    low = text.lower()
    assert "ما يحدد بيوت أشخاص ولا هويات" not in text
    assert "1st" not in text
    assert "measured best" not in low
    assert "the best" not in low
    assert "10.9" in text and "8.7" in text
    assert "H-RANK-01" in text
    assert "stops at the city" in low
    assert "does not identify a person" in low
    assert "B-PRIV-01" in text
    assert "privacy.html" in text
    assert "does not work offline" in low
