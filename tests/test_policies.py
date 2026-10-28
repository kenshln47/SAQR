"""Privacy, terms, and retention match the modes that exist. Not a finding ID."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_policies_name_the_real_behaviour() -> None:
    privacy = (ROOT / "web/legal/privacy.html").read_text(encoding="utf-8")
    terms = (ROOT / "web/legal/terms.html").read_text(encoding="utf-8")
    retention = (ROOT / "web/legal/retention.html").read_text(encoding="utf-8")
    help_html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert "127.0.0.1" in privacy
    assert "Yandex" in privacy and "Baidu" in privacy
    assert "Gravatar" in privacy
    assert "_saqr_trash" in retention
    assert "LICENSE" in terms
    for page in (privacy, terms, retention):
        assert 'href="/fonts.css"' in page
    assert 'href="/legal/privacy.html"' in help_html
    assert 'href="/legal/terms.html"' in help_html
    assert 'href="/legal/retention.html"' in help_html
    assert "ما يحدد بيوت أشخاص ولا هويات" not in help_html
    assert "privacy.html" in (ROOT / "README.md").read_text(encoding="utf-8")
