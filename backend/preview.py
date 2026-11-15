"""Earth terrain preview rendering (hillshaded colour relief) to an inline PNG.

Display only: the colour stretch uses the 2nd-98th elevation percentiles of
the analysed window and has no scientific meaning. NoData is transparent.
"""

from __future__ import annotations

import base64
import struct
import zlib

import numpy as np

# Colour stops (position 0-1, RGB): low terrain dark blue-grey to high terrain pale.
_STOPS = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
_COLORS = np.array(
    [
        [46, 64, 87],
        [74, 122, 98],
        [176, 160, 104],
        [168, 112, 72],
        [236, 228, 216],
    ],
    dtype=np.float64,
)


def _hillshade(z: np.ndarray, cell_size_m: float, azimuth_deg=315.0, altitude_deg=45.0) -> np.ndarray:
    zf = np.where(np.isfinite(z), z, np.nanmean(z) if np.isfinite(z).any() else 0.0)
    gy, gx = np.gradient(zf, cell_size_m)
    slope = np.arctan(np.hypot(gx, gy))
    # ESRI convention: aspect = atan2(dz/dy_north, -dz/dx_east). Row index
    # increases southwards, so dz/dy_north = -gy.
    aspect = np.arctan2(-gy, -gx)
    az = np.radians(360.0 - azimuth_deg + 90.0)
    alt = np.radians(altitude_deg)
    shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    return np.clip(shade, 0.0, 1.0)


def render_rgba(z: np.ndarray, valid: np.ndarray, cell_size_m: float) -> np.ndarray:
    h, w = z.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    if not valid.any():
        return rgba
    lo, hi = np.percentile(z[valid], [2, 98])
    span = hi - lo if hi > lo else 1.0
    t = np.clip((np.where(valid, z, lo) - lo) / span, 0.0, 1.0)
    rgb = np.stack([np.interp(t, _STOPS, _COLORS[:, i]) for i in range(3)], axis=-1)
    shade = _hillshade(z, cell_size_m)
    rgb = rgb * (0.45 + 0.55 * shade[..., None])
    rgba[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    rgba[..., 3] = np.where(valid, 255, 0).astype(np.uint8)
    return rgba


def encode_png(rgba: np.ndarray) -> bytes:
    """Minimal RGBA8 PNG encoder (no external imaging dependency)."""
    h, w, _ = rgba.shape
    raw = b"".join(b"\x00" + rgba[row].tobytes() for row in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")


def png_data_url(z: np.ndarray, valid: np.ndarray, cell_size_m: float) -> str:
    png = encode_png(render_rgba(z, valid, cell_size_m))
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")
