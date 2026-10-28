"""The HTML report loads the font it names. L-REPORT-FONT."""
from __future__ import annotations

from pathlib import Path

from app.report import render_html

ROOT = Path(__file__).resolve().parents[1]


def test_report_links_the_vendored_font() -> None:
    page = render_html("case-1", "# عنوان\n\nنص")
    assert '<link rel="stylesheet" href="/fonts.css">' in page
    assert '<link rel="stylesheet" href="/report.css">' in page
    assert "<style>" not in page
    css = (ROOT / "web/report.css").read_text(encoding="utf-8")
    assert "IBM Plex Sans Arabic" in css
    assert "IBM Plex Sans Arabic" in (ROOT / "web/fonts.css").read_text(encoding="utf-8")
