"""The tool wrappers must refuse closed imagery before they spawn a script."""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("SAQR_CASES", tempfile.mkdtemp(prefix="saqr-cases-"))

import pytest

import app.tools as T


def _clear(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("SAQR_GOOGLE_KEY", "GOOGLE_MAPS_API_KEY", "SAQR_APPLE_KEY", "SAQR_BING_KEY", "SAQR_YANDEX_KEY"):
        monkeypatch.delenv(name, raising=False)


def test_google_tools_do_not_spawn_without_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear(monkeypatch)
    calls: list = []
    monkeypatch.setattr(T, "run_script", lambda *args, **kwargs: calls.append(args) or (0, ""))
    near = T.streetview_near(None, 24.7, 46.7)
    views = T.streetview_views(None, 24.7, 46.7)
    sweep = T.streetview_sweep(None, 24.7, 46.7, provider="google")
    sat = T.satellite(None, 24.7, 46.7, source="google")
    bing = T.satellite(None, 24.7, 46.7, source="bing")
    wayback = T.satellite(None, 24.7, 46.7, source="wayback:2020")
    assert near.is_error and views.is_error and sweep.is_error and sat.is_error and bing.is_error
    assert "SAQR_BING_KEY" in bing.text
    assert wayback.is_error and "not called" in wayback.text and "not restored" in wayback.text
    assert calls == []


class _Case:
    def __init__(self, folder):
        self.dir = folder


def test_esri_world_imagery_is_called_through_zoom_19(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _clear(monkeypatch)
    calls: list = []
    monkeypatch.setattr(T, "run_script", lambda *args, **kwargs: calls.append(args) or (0, ""))
    case = _Case(tmp_path)
    img = tmp_path / "work" / "sat_24.7000_46.7000_z19_esri.jpg"
    img.parent.mkdir(parents=True)
    img.write_bytes(b"jpeg")
    out = T.satellite(case, 24.7, 46.7, zoom=20, source="esri")
    assert calls and calls[0][1] == "tiles.py"
    args = calls[0][2]
    assert args[args.index("--source") + 1] == "esri"
    assert args[args.index("--zoom") + 1] == "19"
    assert "Esri, Maxar, Earthstar Geographics" in out.text
    assert out.is_error is False


def test_sweep_default_is_mapillary(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _clear(monkeypatch)
    calls: list = []
    monkeypatch.setattr(T, "run_script", lambda case, script, args, **kwargs: calls.append((script, args)) or (0, ""))

    class _Case:
        def __init__(self, folder):
            self.dir = folder

    out = T.streetview_sweep(_Case(tmp_path), 24.7, 46.7)
    assert len(calls) == 1
    script, args = calls[0]
    assert script == "pano.py"
    assert args[args.index("--provider") + 1] == "mapillary"
    assert out.is_error
    assert "mapillary" in out.text
