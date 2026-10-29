"""The equirectangular crop keeps the frame and does not invent a coordinate."""
from __future__ import annotations

from PIL import Image

from bench.crop import perspective_crop


def test_equirect_crop_is_narrower_than_the_frame() -> None:
    im = Image.new("RGB", (3600, 1800), (10, 20, 30))
    out, how = perspective_crop(im)
    assert how == "equirect-crop-90deg"
    assert out.size[0] < im.size[0]
    assert out.size[1] == 900


def test_flat_frame_is_unchanged() -> None:
    im = Image.new("RGB", (800, 600), (1, 2, 3))
    out, how = perspective_crop(im)
    assert how == "flat"
    assert out.size == (800, 600)
