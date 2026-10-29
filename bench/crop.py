"""Turn a Panoramax equirectangular frame into one perspective crop.

The crop does not move the camera. Truth stays the GPS point on the manifest.
A frame that is already not 2:1 is returned unchanged.
"""
from __future__ import annotations

from PIL import Image


def perspective_crop(im: Image.Image, fov_deg: float = 90.0) -> tuple[Image.Image, str]:
    im = im.convert("RGB")
    w, h = im.size
    if h <= 0 or w < h * 1.5:
        return im, "flat"
    cw = max(1, int(round(w * (fov_deg / 360.0))))
    ch = max(1, int(round(h * 0.5)))
    x0 = max(0, (w - cw) // 2)
    y0 = max(0, (h - ch) // 2)
    return im.crop((x0, y0, min(w, x0 + cw), min(h, y0 + ch))), "equirect-crop-90deg"
