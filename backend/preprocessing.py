"""Physical-scale harmonization of Earth and Mars DEMs.

Each DEM is handled independently on its own planetary body:

1. A local azimuthal equidistant (AEQD) projection is built on the DEM's *own*
   geodetic CRS (Earth ellipsoid for uploads, the 3,396,000 m Mars sphere for
   MOLA), centred on the raster centre. Distances from the centre are true in
   metres, so no Earth geodesy is ever applied to Mars and degrees are never
   treated as metres.
2. The physical pixel spacing and the largest centred square that fits inside
   the raster are measured in that local metric frame.
3. Both DEMs are resampled onto square grids with the same cell size (the
   coarser of the two native spacings) and the same number of cells, so both
   grids cover the same ground footprint in metres. A DEM that is finer than
   the common cell size is area-averaged, which never creates detail finer
   than the source.
4. A DEM whose native spacing already equals the common cell size (to within
   ALIGNED_MAX_SCALE_ERROR) is NOT averaged. Averaging at a ~1:1 ratio onto a
   grid that is offset from the source pixels blends up to four neighbouring
   pixels: an extra low-pass filter that only the coarser DEM would receive.
   Instead, the grid is shifted (by less than one cell) so that its cell
   centres fall on source pixel centres, and each cell takes exactly one
   source pixel. This is accepted only if the mapping is verified to be a
   one-to-one re-indexing of a contiguous block of source pixels; otherwise
   area averaging is used.
5. NoData is propagated through a separate coverage raster: a harmonized cell
   is valid only if valid source pixels cover at least MIN_CELL_COVERAGE of it.
   NoData values never enter the elevation average. In aligned sampling a cell
   is valid exactly when its single source pixel is valid.

Earth and Mars grids are never placed in a shared CRS and absolute elevations
are never compared; only datum-independent descriptors are compared later.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyproj
import rasterio
from pyproj.crs import ProjectedCRS
from pyproj.crs.coordinate_operation import AzimuthalEquidistantConversion
from rasterio.crs import CRS as RioCRS
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject
from rasterio.windows import Window

import errors
import settings

GDAL_ENV = {
    # Never scan the upload's temporary directory for sidecar files.
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    # Report vertical CRS information (compound CRS) when a GeoTIFF carries it.
    "GTIFF_REPORT_COMPD_CS": "YES",
}


@dataclass(frozen=True)
class DemSource:
    """A validated DEM on disk plus its measured geometry."""

    path: Path
    body: str  # "earth" or "mars"
    horizontal_crs: pyproj.CRS
    vertical_to_metres: float
    center_lon: float
    center_lat: float
    local_crs_wkt: str
    native_spacing_m: float  # conservative: the larger of the two axes
    spacing_xy_m: tuple[float, float]
    half_extent_m: float  # half side of the largest centred square inside the raster


@dataclass(frozen=True)
class HarmonizedGrid:
    elevation_m: np.ndarray  # (n, n) float64, NaN where invalid
    valid: np.ndarray  # (n, n) bool
    resolution_m: float
    cells: int
    # "average": area-weighted aggregation of finer source pixels.
    # "aligned": one source pixel per cell, no interpolation (near-native spacing).
    sampling: str = "average"
    # Aligned sampling only: largest ground distance (m) between a cell centre
    # and the centre of the source pixel it takes its value from.
    max_offset_m: float = 0.0

    @property
    def valid_fraction(self) -> float:
        return float(self.valid.mean())

    @property
    def footprint_m(self) -> float:
        return self.resolution_m * self.cells


def rio_crs(crs: pyproj.CRS) -> RioCRS:
    return RioCRS.from_wkt(crs.to_wkt())


def local_metric_crs(horizontal_crs: pyproj.CRS, lon: float, lat: float) -> pyproj.CRS:
    """AEQD centred on (lon, lat) on the same geodetic CRS (same body and datum)."""
    conversion = AzimuthalEquidistantConversion(
        latitude_natural_origin=lat, longitude_natural_origin=lon
    )
    return ProjectedCRS(conversion=conversion, geodetic_crs=horizontal_crs.geodetic_crs)


def _transformer(src: pyproj.CRS, dst: pyproj.CRS) -> pyproj.Transformer:
    return pyproj.Transformer.from_crs(src, dst, always_xy=True)


def _apply(transform, cols, rows):
    """Affine pixel (col, row) -> map (x, y); works on scalars and arrays."""
    t = transform
    return t.a * cols + t.b * rows + t.c, t.d * cols + t.e * rows + t.f


def describe_source(
    path: Path,
    body: str,
    horizontal_crs: pyproj.CRS,
    transform,
    width: int,
    height: int,
    vertical_to_metres: float,
) -> DemSource:
    """Measure centre, physical pixel spacing and usable centred extent."""
    to_geo = _transformer(horizontal_crs, horizontal_crs.geodetic_crs)
    cx, cy = _apply(transform, width / 2.0, height / 2.0)
    lon, lat = to_geo.transform(cx, cy)
    if not (math.isfinite(lon) and math.isfinite(lat)) or abs(lat) > 89.0:
        raise errors.fail(
            errors.UNSUPPORTED_CRS,
            "The raster centre could not be located on the planet, or it lies too "
            "close to a pole for the local metric projection.",
        )
    local = local_metric_crs(horizontal_crs, lon, lat)
    to_local = _transformer(horizontal_crs, local)

    # Pixel spacing at the raster centre, measured as true ground distance.
    col, row = width / 2.0, height / 2.0
    pts = [_apply(transform, col, row), _apply(transform, col + 1, row), _apply(transform, col, row + 1)]
    xs, ys = to_local.transform([p[0] for p in pts], [p[1] for p in pts])
    dx = math.hypot(xs[1] - xs[0], ys[1] - ys[0])
    dy = math.hypot(xs[2] - xs[0], ys[2] - ys[0])
    lo, hi = settings.PIXEL_SPACING_RANGE_M
    if not all(math.isfinite(v) and lo <= v <= hi for v in (dx, dy)):
        raise errors.fail(
            errors.INVALID_DEM,
            "The raster pixel spacing is not physically plausible "
            f"(measured {dx:.4g} m by {dy:.4g} m).",
        )

    # Largest centred, axis-aligned square inside the raster outline.
    samples = 256
    t = np.linspace(0.0, 1.0, samples)
    edge_cols = np.concatenate([t * width, t * width, np.zeros(samples), np.full(samples, width)])
    edge_rows = np.concatenate([np.zeros(samples), np.full(samples, height), t * height, t * height])
    ex, ey = _apply(transform, edge_cols, edge_rows)
    lx, ly = to_local.transform(ex, ey)
    lx, ly = np.asarray(lx), np.asarray(ly)
    if not (np.all(np.isfinite(lx)) and np.all(np.isfinite(ly))):
        raise errors.fail(errors.UNSUPPORTED_CRS, "The raster outline could not be projected.")
    half_extent = float(np.min(np.maximum(np.abs(lx), np.abs(ly))))

    return DemSource(
        path=path,
        body=body,
        horizontal_crs=horizontal_crs,
        vertical_to_metres=vertical_to_metres,
        center_lon=float(lon),
        center_lat=float(lat),
        local_crs_wkt=local.to_wkt(),
        native_spacing_m=max(dx, dy),
        spacing_xy_m=(dx, dy),
        half_extent_m=half_extent,
    )


def plan_common_grid(earth: DemSource, mars: DemSource) -> tuple[float, int]:
    """Common cell size (coarser native spacing) and cell count (equal footprint)."""
    resolution = max(earth.native_spacing_m, mars.native_spacing_m)
    half = min(earth.half_extent_m, mars.half_extent_m)
    cells = int(math.floor(2.0 * half / resolution))
    if cells < settings.MIN_GRID_CELLS:
        raise errors.fail(
            errors.INSUFFICIENT_EXTENT,
            "The common comparison area is too small for the common resolution: "
            f"{cells} x {cells} cells of {resolution:.1f} m (minimum "
            f"{settings.MIN_GRID_CELLS} x {settings.MIN_GRID_CELLS}). The Earth DEM must "
            f"cover at least {settings.MIN_GRID_CELLS * resolution / 1000:.1f} km by "
            f"{settings.MIN_GRID_CELLS * resolution / 1000:.1f} km around its centre.",
        )
    return resolution, cells


def _read_footprint(source: DemSource, half_side: float, margin_m: float):
    """Read only the source pixels needed for a centred square footprint."""
    local = pyproj.CRS.from_wkt(source.local_crs_wkt)
    to_src = _transformer(local, source.horizontal_crs)
    h = half_side + margin_m
    t = np.linspace(-h, h, 129)
    bx = np.concatenate([t, t, np.full_like(t, -h), np.full_like(t, h)])
    by = np.concatenate([np.full_like(t, -h), np.full_like(t, h), t, t])
    sx, sy = to_src.transform(bx, by)

    with rasterio.Env(**GDAL_ENV), rasterio.open(source.path) as ds:
        cols, rows = _apply(~ds.transform, np.asarray(sx), np.asarray(sy))
        if not (np.all(np.isfinite(cols)) and np.all(np.isfinite(rows))):
            raise errors.fail(errors.UNSUPPORTED_CRS, "The comparison window could not be mapped onto the raster.")
        c0 = max(int(math.floor(cols.min())) - 2, 0)
        r0 = max(int(math.floor(rows.min())) - 2, 0)
        c1 = min(int(math.ceil(cols.max())) + 2, ds.width)
        r1 = min(int(math.ceil(rows.max())) + 2, ds.height)
        if c1 <= c0 or r1 <= r0:
            raise errors.fail(errors.INSUFFICIENT_VALID_DATA, "The comparison window contains no raster pixels.")
        if (c1 - c0) * (r1 - r0) > settings.MAX_READ_WINDOW_PIXELS:
            raise errors.fail(
                errors.RASTER_TOO_LARGE,
                "The comparison window would require decoding "
                f"{(c1 - c0) * (r1 - r0):,} pixels (limit "
                f"{settings.MAX_READ_WINDOW_PIXELS:,}). Upload a coarser or smaller DEM.",
            )
        window = Window(c0, r0, c1 - c0, r1 - r0)
        try:
            band = ds.read(1, window=window, masked=True)
        except rasterio.errors.RasterioError as exc:
            raise errors.fail(errors.INVALID_DEM, "The elevation values could not be read from the GeoTIFF.") from exc
        win_transform = ds.window_transform(window)

    data = np.ma.filled(band.astype(np.float64), np.nan)
    data[~np.isfinite(data)] = np.nan
    data *= source.vertical_to_metres
    return data, win_transform


def _check_plausible(data: np.ndarray, body: str) -> None:
    valid = data[np.isfinite(data)]
    if valid.size == 0:
        raise errors.fail(
            errors.INSUFFICIENT_VALID_DATA,
            "The DEM has no valid elevation values in the comparison window (empty or fully masked).",
        )
    lo, hi = settings.ELEVATION_RANGE_M[body]
    vmin, vmax = float(valid.min()), float(valid.max())
    if vmin < lo or vmax > hi:
        raise errors.fail(
            errors.INVALID_DEM,
            f"Elevations range from {vmin:.6g} m to {vmax:.6g} m, outside the plausible "
            f"{body.capitalize()} range ({lo:.0f} m to {hi:.0f} m). Check the vertical units "
            "and make sure NoData values are declared in the GeoTIFF.",
        )


def _resample(data, src_transform, src_crs, dst_transform, dst_crs, cells):
    elevation = np.full((cells, cells), np.nan, dtype=np.float64)
    reproject(
        source=data,
        destination=elevation,
        src_transform=src_transform,
        src_crs=src_crs,
        src_nodata=np.nan,
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        dst_nodata=np.nan,
        resampling=Resampling.average,
    )
    coverage = np.zeros((cells, cells), dtype=np.float32)
    reproject(
        source=np.isfinite(data).astype(np.float32),
        destination=coverage,
        src_transform=src_transform,
        src_crs=src_crs,
        src_nodata=None,
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        dst_nodata=None,
        init_dest_nodata=False,
        resampling=Resampling.average,
    )
    valid = (coverage >= settings.MIN_CELL_COVERAGE) & np.isfinite(elevation)
    elevation[~valid] = np.nan
    return elevation, valid


def near_native(source: DemSource, resolution_m: float) -> bool:
    """True if the cell size matches the source spacing on both axes within tolerance."""
    return all(abs(resolution_m / d - 1.0) <= settings.ALIGNED_MAX_SCALE_ERROR for d in source.spacing_xy_m)


def _aligned_indices(source: DemSource, win_transform, shape, resolution_m: float, cells: int):
    """Source (rows, cols) for a pixel-aligned grid, or None if no clean 1:1 mapping exists.

    The (cells x cells) grid of resolution_m metres is centred on the raster
    centre in the local metric CRS and then shifted, by less than one cell, so
    that its central cell centre coincides with a source pixel centre. The
    mapping is accepted only if every cell maps to a distinct source pixel and
    the pixels form a contiguous block in the same row/column order, i.e. the
    result is a pure re-indexing of existing pixels with nothing duplicated,
    skipped or interpolated. Out-of-raster pixels are returned as -1.
    """
    if cells < 2:
        return None
    local = pyproj.CRS.from_wkt(source.local_crs_wkt)
    to_src = _transformer(local, source.horizontal_crs)
    to_local = _transformer(source.horizontal_crs, local)
    inv = ~win_transform
    half = resolution_m * cells / 2.0
    centres = -half + (np.arange(cells) + 0.5) * resolution_m  # east offsets; north = -centres[row]
    k = cells // 2

    # Shift so that the central cell centre lands on its source pixel centre.
    sx, sy = to_src.transform(centres[k], -centres[k])
    col, row = _apply(inv, sx, sy)
    if not (math.isfinite(col) and math.isfinite(row)):
        return None
    px, py = _apply(win_transform, math.floor(col) + 0.5, math.floor(row) + 0.5)
    lx, ly = to_local.transform(px, py)
    shift_x, shift_y = lx - centres[k], ly + centres[k]
    if max(abs(shift_x), abs(shift_y)) > resolution_m:
        return None

    gx, gy = np.meshgrid(centres + shift_x, -centres + shift_y)
    sx, sy = to_src.transform(gx.ravel(), gy.ravel())
    col, row = _apply(inv, np.asarray(sx), np.asarray(sy))
    if not (np.all(np.isfinite(col)) and np.all(np.isfinite(row))):
        return None
    ci = np.floor(col).astype(np.int64).reshape(cells, cells)
    ri = np.floor(row).astype(np.int64).reshape(cells, cells)

    # Required lattice: unit steps along grid rows/columns, mutually orthogonal.
    step_e = (ci[k, k + 1] - ci[k, k], ri[k, k + 1] - ri[k, k])
    step_s = (ci[k + 1, k] - ci[k, k], ri[k + 1, k] - ri[k, k])
    units = {(1, 0), (-1, 0), (0, 1), (0, -1)}
    if step_e not in units or step_s not in units or step_e[0] * step_s[0] + step_e[1] * step_s[1] != 0:
        return None
    jj, ii = np.indices((cells, cells))
    expect_c = ci[k, k] + (ii - k) * step_e[0] + (jj - k) * step_s[0]
    expect_r = ri[k, k] + (ii - k) * step_e[1] + (jj - k) * step_s[1]
    if not (np.array_equal(ci, expect_c) and np.array_equal(ri, expect_r)):
        return None

    # Positional error actually incurred: cell centre vs. source pixel centre.
    px, py = _apply(win_transform, ci.ravel() + 0.5, ri.ravel() + 0.5)
    lx, ly = to_local.transform(px, py)
    max_offset = float(np.max(np.hypot(np.asarray(lx) - gx.ravel(), np.asarray(ly) - gy.ravel())))

    inside = (ri >= 0) & (ri < shape[0]) & (ci >= 0) & (ci < shape[1])
    return np.where(inside, ri, -1), np.where(inside, ci, -1), max_offset


def harmonize(source: DemSource, resolution_m: float, cells: int) -> HarmonizedGrid:
    """Resample a DEM onto a (cells x cells) grid of resolution_m metres around its centre.

    Finer sources are area-averaged. A source already at the cell size is
    sampled pixel-for-pixel on its own lattice (see the module docstring).
    """
    half_side = resolution_m * cells / 2.0
    data, win_transform = _read_footprint(source, half_side, margin_m=2 * resolution_m)
    _check_plausible(data, source.body)

    if near_native(source, resolution_m):
        aligned = _aligned_indices(source, win_transform, data.shape, resolution_m, cells)
        if aligned is not None:
            rows, cols, max_offset = aligned
            inside = rows >= 0
            elevation = np.full((cells, cells), np.nan, dtype=np.float64)
            elevation[inside] = data[rows[inside], cols[inside]]
            valid = np.isfinite(elevation)
            return HarmonizedGrid(
                elevation_m=elevation,
                valid=valid,
                resolution_m=resolution_m,
                cells=cells,
                sampling="aligned",
                max_offset_m=max_offset,
            )

    dst_transform = from_origin(-half_side, half_side, resolution_m, resolution_m)
    elevation, valid = _resample(
        data,
        win_transform,
        rio_crs(source.horizontal_crs),
        dst_transform,
        RioCRS.from_wkt(source.local_crs_wkt),
        cells,
    )
    return HarmonizedGrid(elevation_m=elevation, valid=valid, resolution_m=resolution_m, cells=cells)


def preview_grid(source: DemSource, footprint_m: float) -> HarmonizedGrid:
    """Grid for the preview image: same footprint, never finer than the source."""
    cells = settings.PREVIEW_MAX_PIXELS_PER_SIDE
    resolution = max(source.native_spacing_m, footprint_m / cells)
    cells = max(int(round(footprint_m / resolution)), 1)
    return harmonize(source, footprint_m / cells, cells)
