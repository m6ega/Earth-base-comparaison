"""Shared fixtures: SYNTHETIC, geospatially valid Earth GeoTIFFs.

These rasters are generated from analytic surfaces with known properties to
test mathematics and API behaviour. They are NOT real-world observations.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

UTM33N = "EPSG:32633"  # WGS 84 / UTM zone 33N, metres
ORIGIN = (440_000.0, 4_520_000.0)


def synthetic_surface(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Hilly analytic terrain in metres: waves + regional tilt + a bowl-shaped crater."""
    r = np.hypot(x - 30_000.0, y + 30_000.0)
    crater = -400.0 * np.exp(-((r / 9_000.0) ** 2)) + 120.0 * np.exp(-(((r - 11_000.0) / 2_500.0) ** 2))
    waves = 180.0 * np.sin(2 * np.pi * x / 14_000.0) * np.cos(2 * np.pi * y / 19_000.0)
    ripples = 25.0 * np.sin(2 * np.pi * (x + y) / 2_300.0)
    return 900.0 + 0.004 * x + waves + ripples + crater


def write_dem(
    path: Path,
    data: np.ndarray,
    *,
    crs: str | None = UTM33N,
    transform=None,
    nodata: float | None = -9999.0,
    units: str | None = "metre",
    dtype: str = "float32",
    count: int = 1,
) -> Path:
    h, w = data.shape
    profile = {
        "driver": "GTiff",
        "width": w,
        "height": h,
        "count": count,
        "dtype": dtype,
        "transform": transform if transform is not None else from_origin(*ORIGIN, 50.0, 50.0),
        "compress": "deflate",
    }
    if crs is not None:
        profile["crs"] = crs
    if nodata is not None:
        profile["nodata"] = nodata
    with rasterio.open(path, "w", **profile) as dst:
        for b in range(1, count + 1):
            dst.write(data.astype(dtype), b)
        if units is not None:
            dst.units = tuple([units] * count)
    return path


def utm_grid(size: int, pixel_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Ground coordinates (metres from the north-west corner) of pixel centres."""
    c = (np.arange(size) + 0.5) * pixel_m
    x, y = np.meshgrid(c, -c)
    return x, y


@pytest.fixture
def synthetic_dem(tmp_path) -> Path:
    """60 km x 60 km synthetic Earth DEM at 50 m in UTM 33N, units metre, NoData -9999."""
    x, y = utm_grid(1200, 50.0)
    return write_dem(tmp_path / "synthetic_earth.tif", synthetic_surface(x, y))
