"""M-CAT-01: a dead model list must not kill a run, and a stale list is better than an exception."""
from __future__ import annotations

import pytest
import requests

from app import openrouter as OR


def _down(*_args, **_kwargs):
    raise requests.ConnectionError("down")


def test_a_failed_refresh_keeps_the_stale_list(monkeypatch: pytest.MonkeyPatch) -> None:
    OR._cat["at"] = 0.0
    OR._cat["models"] = {"old": {"id": "old"}}
    monkeypatch.setattr(OR.requests, "get", _down)
    assert OR.catalog()["old"]["id"] == "old"


def test_reasoning_skips_the_parameter_when_nothing_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    OR._cat["at"] = 0.0
    OR._cat["models"] = {}
    monkeypatch.setattr(OR.requests, "get", _down)
    assert OR.reasoning("anthropic/claude-opus-5.5", "high") == {}


def test_reasoning_uses_a_stale_row(monkeypatch: pytest.MonkeyPatch) -> None:
    OR._cat["at"] = 0.0
    OR._cat["models"] = {"m": {"id": "m", "supported_parameters": ["reasoning"]}}
    monkeypatch.setattr(OR.requests, "get", _down)
    assert OR.reasoning("m", "high") == {"reasoning": {"effort": "high"}}
    assert OR.reasoning("missing", "low") == {}
