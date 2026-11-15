"""Methodology 0.4: artefact-free resampling of rotated and near-native grids.

GDAL area averaging at ratios near 1:1, or on grids rotated relative to the
local east/north frame, mixes a varying number of source pixels per cell. The
0.3 audit measured Shackleton 3x3 roughness 1.30 m native -> 4.65 m processed.
These tests pin the corrected behaviour. They use the real lunar references and
synthetic Earth surfaces (mathematical controls, not analog ground truth).
"""

from __future__ import annotations

import math

import numpy as np
import pytest
import rasterio
import rasterio.crs
import rasterio.transform
import rasterio.warp
from rasterio.transform import Affine

import analysis
import preprocessing
import settings
import similarity
import terrain_features as tf
from conftest import ORIGIN, synthetic_surface, write_dem
from preprocessing import HarmonizedGrid, harmonize
from reference import load_reference
from validation import open_earth_dem

MOON = ["moon-shackleton", "moon-mons-mouton"]


def _native_and_production(rid, ratio=1.0, max_cells=355):
    src = load_reference(rid).source
    res = round(src.native_spacing_m * ratio, 6)
    cells = min(int(2 * src.half_extent_m * 0.95 // res), max_cells)
    prod = harmonize(src, res, cells)
    with rasterio.open(src.path) as ds:
        a = ds.read(1, masked=True).astype(np.float64).filled(np.nan)
    n = min(int(cells * ratio), *a.shape)
    r0, c0 = (a.shape[0] - n) // 2, (a.shape[1] - n) // 2
    return src, a[r0:r0 + n, c0:c0 + n], prod


def _laplacian_std(z):
    lap = 4 * z[1:-1, 1:-1] - z[:-2, 1:-1] - z[2:, 1:-1] - z[1:-1, :-2] - z[1:-1, 2:]
    return float(np.nanstd(lap))


def _features(z, cell):
    return analysis.compute_features(HarmonizedGrid(z, np.isfinite(z), cell, z.shape[0]), "x")


def _similarity(fa, fb):
    s = {m: similarity.distribution_similarity(fa.scoring_histograms[m], fb.scoring_histograms[m]) for m in analysis.METRICS}
    return s, similarity.total_similarity(s)


def test_methodology_version_bumped():
    assert settings.METHODOLOGY_VERSION == "0.4-proposal"


@pytest.mark.parametrize("rid", MOON)
def test_moon_reference_rotation_is_detected(rid):
    src = load_reference(rid).source
    data, wt = preprocessing._read_footprint(src, 20 * src.native_spacing_m, 2 * src.native_spacing_m)
    assert preprocessing.grid_rotation_deg(src, wt, data.shape) > settings.AREA_AVERAGE_MAX_ROTATION_DEG


@pytest.mark.parametrize("rid", MOON)
def test_moon_roughness_not_inflated_at_native_resolution(rid):
    src, native, prod = _native_and_production(rid)
    assert prod.sampling == "interpolated"
    rough_native = np.nanmean(tf.roughness_rms(native, 3))
    rough_prod = np.nanmean(tf.roughness_rms(prod.elevation_m, 3))
    # 0.3 inflated these 1.5-3.6x. Interpolating a rotated grid may only smooth.
    assert 0.6 * rough_native <= rough_prod <= 1.02 * rough_native
    assert _laplacian_std(prod.elevation_m) <= 1.02 * _laplacian_std(native)
    slope_native = np.nanmean(tf.slope_degrees(native, prod.resolution_m))
    assert np.nanmean(tf.slope_degrees(prod.elevation_m, prod.resolution_m)) == pytest.approx(slope_native, rel=0.06)


@pytest.mark.parametrize("rid", MOON)
def test_moon_self_similarity_native_vs_processed(rid):
    _, native, prod = _native_and_production(rid)
    scores, total = _similarity(_features(native, prod.resolution_m), _features(prod.elevation_m, prod.resolution_m))
    assert total > 0.90, scores  # 0.3: 0.771 (Shackleton), 0.878 (Mons Mouton)
    assert scores["surface_roughness"] > 0.80, scores  # 0.3: 0.361, 0.699


@pytest.mark.parametrize("rid", MOON)
def test_moon_downsampled_reference_has_no_average_artefacts(rid):
    """Coarse Earth inputs make the reference downsample on its rotated grid (0.3 still used GDAL average)."""
    _, _, prod2 = _native_and_production(rid, ratio=2.0, max_cells=170)
    _, _, prod3 = _native_and_production(rid, ratio=3.0, max_cells=110)
    assert prod2.sampling == prod3.sampling == "interpolated"
    r2 = np.nanmean(tf.roughness_rms(prod2.elevation_m, 3))
    r3 = np.nanmean(tf.roughness_rms(prod3.elevation_m, 3))
    assert r3 > r2  # larger cells span more relief; 0.3 'average' was non-monotonic here


@pytest.mark.parametrize("rid", ["mars-gale", "mars-amazonis"])
def test_mars_references_not_degraded(rid):
    """Mars grids are not rotated; 0.4 must not move them further from their native
    pixels than the 0.3 method (GDAL average) did. Amazonis pixels are anisotropic
    (438 x 463 m), so its raw array is only an approximate oracle: compare relatively."""
    src, native, prod = _native_and_production(rid, max_cells=214)
    cell, cells = prod.resolution_m, prod.cells
    half = cell * cells / 2
    data, wt = preprocessing._read_footprint(src, half, 2 * cell)
    old, _ = preprocessing._reproject_pair(
        data, wt, preprocessing.rio_crs(src.horizontal_crs), rasterio.transform.from_origin(-half, half, cell, cell),
        rasterio.crs.CRS.from_wkt(src.local_crs_wkt), cells, rasterio.warp.Resampling.average)
    oracle = _features(native, cell)
    _, new_total = _similarity(oracle, _features(prod.elevation_m, cell))
    _, old_total = _similarity(oracle, _features(old, cell))
    assert new_total >= old_total - 0.02, (new_total, old_total)
    if rid == "mars-gale":  # near-isotropic pixels (0.45 %): absolute check is meaningful
        assert new_total > 0.95


def test_box_weights_are_exact_area_weights():
    assert np.array_equal(preprocessing._box_weights(1.0), [1.0])
    w = preprocessing._box_weights(1.5)
    assert w == pytest.approx([0.25 / 1.5, 1 / 1.5, 0.25 / 1.5])
    for width in (1.0, 2.0, 2.7, 9.3):
        assert preprocessing._box_weights(width).sum() == pytest.approx(1.0)


def _rotated_earth(tmp_path, name, angle_deg, px=50.0, n=1200, units="metre", holes=False, scale=None, offset=None):
    """Synthetic surface sampled at the centres of a (possibly rotated) UTM pixel grid."""
    t = Affine.translation(*ORIGIN) * Affine.rotation(angle_deg) * Affine.scale(px, -px)
    cols, rows = np.meshgrid(np.arange(n) + 0.5, np.arange(n) + 0.5)
    x, y = t * (cols, rows)
    centre_x, centre_y = t * (n / 2, n / 2)
    z = synthetic_surface(x - centre_x + 30_000, y - centre_y - 30_000)
    if holes:
        rng = np.random.default_rng(4)
        z[rng.random(z.shape) < 0.15] = np.nan
    data = np.where(np.isfinite(z), z, -9999.0)
    dtype = "float32"
    if scale is not None:
        data = np.where(np.isfinite(z), np.round((z - offset) / scale), -9999).astype("int16")
        dtype = "int16"
    path = write_dem(tmp_path / name, data.astype(dtype), transform=t, units=units, dtype=dtype)
    if scale is not None:
        with rasterio.open(path, "r+") as ds:
            ds.scales, ds.offsets = (scale,), (offset,)
    return path


def _earth_grid(path, resolution, cells):
    return harmonize(open_earth_dem(path)[0], resolution, cells)


@pytest.mark.parametrize("ratio_cell", [463.0, 80.0])
def test_rotated_earth_dem_matches_unrotated(tmp_path, ratio_cell):
    """The same terrain on a 30-degree-rotated grid must give the same descriptors."""
    straight = _earth_grid(_rotated_earth(tmp_path, "r0.tif", 0.0), ratio_cell, 90)
    rotated = _earth_grid(_rotated_earth(tmp_path, "r30.tif", 30.0), ratio_cell, 90)
    # 463 m = 9x the 50 m source (aligned: area average); 80 m = 1.6x (near-native: interpolated)
    assert straight.sampling == ("average" if ratio_cell > 100 else "interpolated")
    assert rotated.sampling == "interpolated"
    scores, total = _similarity(_features(straight.elevation_m, ratio_cell), _features(rotated.elevation_m, ratio_cell))
    assert total > 0.95, scores


def test_genuine_aligned_downsampling_still_area_averages(tmp_path):
    grid = _earth_grid(_rotated_earth(tmp_path, "a.tif", 0.0), 463.0, 90)
    assert grid.sampling == "average"


def test_near_native_earth_grid_is_interpolated_not_averaged(tmp_path):
    path = _rotated_earth(tmp_path, "nn.tif", 0.0, px=80.0, n=500)
    earth = open_earth_dem(path)[0]
    res = earth.native_spacing_m * 1.3  # 1 < ratio < 2: GDAL average would mix 1-2 pixels per cell
    assert harmonize(earth, res, 200).sampling == "interpolated"


def test_interpolated_path_respects_nodata(tmp_path):
    path = _rotated_earth(tmp_path, "holes.tif", 30.0, holes=True)
    grid = _earth_grid(path, 463.0, 90)
    assert grid.sampling == "interpolated"
    assert np.all(np.isfinite(grid.elevation_m[grid.valid])) and not np.any(np.isfinite(grid.elevation_m[~grid.valid]))
    with rasterio.open(path) as ds:
        raw = ds.read(1, masked=True)
    assert np.nanmin(grid.elevation_m) >= raw.min() - 1e-6
    assert np.nanmax(grid.elevation_m) <= raw.max() + 1e-6  # no -9999 leakage, no overshoot
    assert grid.valid_fraction > 0.95


def test_interpolated_path_decodes_scale_offset(tmp_path):
    plain = _earth_grid(_rotated_earth(tmp_path, "p.tif", 30.0), 463.0, 90)
    enc = _earth_grid(_rotated_earth(tmp_path, "e.tif", 30.0, scale=0.1, offset=500.0), 463.0, 90)
    assert enc.sampling == "interpolated"
    assert np.nanmax(np.abs(plain.elevation_m - enc.elevation_m)) < 0.06  # 0.1 m quantization


def test_api_reports_methodology_0_4(synthetic_dem):
    from fastapi.testclient import TestClient
    from app import app

    assert TestClient(app).get("/openapi.json").json()["info"]["version"] == "0.4-proposal"
    with synthetic_dem.open("rb") as f:
        r = TestClient(app).post("/analyze", files={"file": ("earth.tif", f)}, data={"reference_id": "moon-shackleton"})
    assert r.status_code == 200, r.text
    codes = {w["code"] for w in r.json()["warnings"]}
    assert "NEAR_NATIVE_INTERPOLATED" in codes  # reference interpolated, disclosed
    message = next(w["message"] for w in r.json()["warnings"] if w["code"] == "NEAR_NATIVE_INTERPOLATED")
    assert "bilinearly interpolated" in message and math.isfinite(r.json()["total_similarity"])
