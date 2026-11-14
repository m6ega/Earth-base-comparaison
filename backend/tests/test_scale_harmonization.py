"""Physical-scale harmonization: synthetic 30 km Earth (10 m) vs Mars (500 m), and the real Gale grid.

Regression for the "coarser DEM smoothed twice" defect: before methodology
0.2, a DEM already at the common cell size was area-averaged onto a grid offset
from its pixels, which blended up to 2 x 2 pixels and cut Mars roughness by up
to ~40 % depending only on whether the cell count was odd or even.

All Earth and Mars rasters here except dem.tif are SYNTHETIC analytic surfaces.
"""

import math

import numpy as np
import pyproj
import pytest
import rasterio
from rasterio.transform import from_origin

import errors
import settings
import similarity
import terrain_features as tf
import validation
from analysis import METRICS, compute_features
from conftest import synthetic_surface, write_dem
from preprocessing import describe_source, harmonize, near_native, plan_common_grid
from reference import load_reference

MARS_EQUATOR_WKT = (
    'PROJCS["Mars_Equirectangular_c0",GEOGCS["Mars",DATUM["D_Mars",SPHEROID["Mars",3396000,0]],'
    'PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Equirectangular"],'
    'PARAMETER["standard_parallel_1",0],PARAMETER["central_meridian",0],PARAMETER["false_easting",0],'
    'PARAMETER["false_northing",0],UNIT["metre",1]]'
)
SIDE_M = 30_000.0
EARTH_PIX, EARTH_N = 10.0, 3000
MARS_PIX, MARS_N = 500.0, 60
# On the UTM 33N central meridian, so the Earth grid is not rotated against true north.
EARTH_ORIGIN = (500_000.0 - SIDE_M / 2, 4_520_000.0)


def offsets(n, pix):
    """Pixel-centre offsets in metres from the north-west corner (same convention on both bodies)."""
    c = (np.arange(n) + 0.5) * pix
    return np.meshgrid(c, -c)


def fine_texture(x, y):
    """3 m amplitude at 80 m wavelength: resolved at 10 m, invisible at 500 m."""
    return 3.0 * np.sin(2 * np.pi * x / 80.0) * np.sin(2 * np.pi * y / 80.0)


def earth_dem(path, surface, nodata_mask=None, n=EARTH_N):
    x, y = offsets(n, EARTH_PIX)
    z = surface(x, y).astype(np.float64)
    if nodata_mask is not None:
        z[nodata_mask] = -9999.0
    write_dem(path, z, transform=from_origin(*EARTH_ORIGIN, EARTH_PIX, EARTH_PIX))
    return validation.open_earth_dem(path)[0]


def mars_dem(path, surface, nodata_mask=None):
    x, y = offsets(MARS_N, MARS_PIX)
    z = surface(x, y).astype(np.float64)
    if nodata_mask is not None:
        z[nodata_mask] = -32768.0
    transform = from_origin(-SIDE_M / 2, SIDE_M / 2, MARS_PIX, MARS_PIX)  # centred on 0 E, 0 N
    write_dem(path, z, crs=MARS_EQUATOR_WKT, transform=transform, nodata=-32768.0)
    with rasterio.open(path) as ds:
        crs = pyproj.CRS.from_wkt(ds.crs.to_wkt())
    return describe_source(path, "mars", crs, transform, MARS_N, MARS_N, 1.0)


def read_raw(source):
    with rasterio.open(source.path) as ds:
        return ds.read(1, masked=True).astype(np.float64).filled(np.nan)


def find_block(grid, raw):
    """(row, col) of the contiguous raw block equal to the grid (NaN-aware), or None."""
    n = grid.shape[0]
    for r0 in range(raw.shape[0] - n + 1):
        for c0 in range(raw.shape[1] - n + 1):
            if np.array_equal(raw[r0 : r0 + n, c0 : c0 + n], grid, equal_nan=True):
                return r0, c0
    return None


def scores(a, b):
    fa, fb = compute_features(a, "A"), compute_features(b, "B")
    return {m: similarity.distribution_similarity(fa.histograms[m], fb.histograms[m]) for m in METRICS}


@pytest.fixture(scope="module")
def scenario(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("scale")
    textured = earth_dem(tmp / "earth_textured.tif", lambda x, y: synthetic_surface(x, y) + fine_texture(x, y))
    smooth = earth_dem(tmp / "earth_smooth.tif", synthetic_surface)
    mars = mars_dem(tmp / "mars.tif", synthetic_surface)
    return {"tmp": tmp, "earth": textured, "earth_smooth": smooth, "mars": mars}


# --- Synthetic 30 km x 30 km scenario: Earth 3000 x 3000 @ 10 m, Mars 60 x 60 @ 500 m ---------------


def test_physical_spacing_and_extent_are_measured_in_metres(scenario):
    earth, mars = scenario["earth"], scenario["mars"]
    assert earth.spacing_xy_m == pytest.approx((10.0, 10.0), rel=1e-3)  # UTM k0 = 0.9996 -> 10.004 m ground
    assert mars.spacing_xy_m == pytest.approx((500.0, 500.0), rel=1e-9)  # Mars sphere, equator: true scale
    assert earth.half_extent_m == pytest.approx(SIDE_M / 2, rel=1e-3)
    assert mars.half_extent_m == pytest.approx(SIDE_M / 2, rel=1e-5)
    assert mars.horizontal_crs.ellipsoid.semi_major_metre == 3_396_000


def test_common_grid_uses_coarser_spacing_and_identical_footprint(scenario):
    earth, mars = scenario["earth"], scenario["mars"]
    res, cells = plan_common_grid(earth, mars)
    assert res == max(earth.native_spacing_m, mars.native_spacing_m) == mars.native_spacing_m
    assert res / earth.native_spacing_m > 49  # Earth is reduced ~50x; nothing is upsampled
    e, m = harmonize(earth, res, cells), harmonize(mars, res, cells)
    assert e.elevation_m.shape == m.elevation_m.shape == (cells, cells)
    assert e.footprint_m == m.footprint_m
    assert SIDE_M - res <= e.footprint_m <= 2 * min(earth.half_extent_m, mars.half_extent_m)
    assert cells * cells <= MARS_N * MARS_N  # no Mars cells invented


@pytest.mark.parametrize("cells", [58, 59])  # both parities: odd counts used to land half a pixel off
def test_coarser_dem_is_sampled_pixel_for_pixel_without_smoothing(scenario, cells):
    mars = scenario["mars"]
    grid = harmonize(mars, mars.native_spacing_m, cells)
    assert grid.sampling == "aligned"
    assert grid.max_offset_m < 1.0  # metres; equator, true-scale pixels
    raw = read_raw(mars)
    assert find_block(grid.elevation_m, raw) is not None  # exact pixel values, contiguous, no blending
    raw_rough = np.nanmedian(tf.roughness_rms(raw, settings.ROUGHNESS_WINDOW_CELLS))
    grid_rough = np.nanmedian(tf.roughness_rms(grid.elevation_m, settings.ROUGHNESS_WINDOW_CELLS))
    assert grid_rough == pytest.approx(raw_rough, rel=0.02)  # was -40 % with the 2x2 blending


def test_scores_do_not_depend_on_cell_count_parity(scenario):
    earth, mars = scenario["earth"], scenario["mars"]
    res = mars.native_spacing_m
    s58 = scores(harmonize(earth, res, 58), harmonize(mars, res, 58))
    s59 = scores(harmonize(earth, res, 59), harmonize(mars, res, 59))
    for m in METRICS:  # before the fix: roughness 0.777 (58) vs 0.455 (59)
        assert s58[m] == pytest.approx(s59[m], abs=0.02)


def test_earth_detail_is_removed_and_mars_detail_is_not_invented(scenario):
    earth, smooth, mars = scenario["earth"], scenario["earth_smooth"], scenario["mars"]
    res, cells = plan_common_grid(earth, mars)
    m = harmonize(mars, res, cells)
    with_texture = scores(harmonize(earth, res, cells), m)
    without_texture = scores(harmonize(smooth, res, cells), m)
    for k in METRICS:  # sub-cell Earth texture has no effect at the common scale
        assert with_texture[k] == pytest.approx(without_texture[k], abs=1e-3)
    # The same landscape at a matched scale is similar. Not 1.0: the synthetic Mars
    # values are point samples while the Earth cells are 500 m area averages.
    assert min(with_texture.values()) > 0.7
    # Negative control: Earth slope at its native 10 m differs strongly from Mars at 500 m.
    with rasterio.open(earth.path) as ds:
        z10 = ds.read(1).astype(np.float64)[1000:2000, 1000:2000]
    naive = similarity.distribution_similarity(
        tf.histogram_fractions(tf.slope_degrees(z10, EARTH_PIX), settings.SLOPE_BIN_EDGES_DEG)[0],
        compute_features(m, "Mars").histograms["slope_distribution"],
    )
    assert naive < 0.6 < with_texture["slope_distribution"]


def test_features_are_in_physical_units_for_both_bodies(scenario):
    tmp, g = scenario["tmp"], 0.05  # 5 % eastward gradient, metres per metre
    earth = earth_dem(tmp / "plane_e.tif", lambda x, y: 1000 + g * x)
    mars = mars_dem(tmp / "plane_m.tif", lambda x, y: 1000 + g * x)
    res, cells = plan_common_grid(earth, mars)
    for src in (earth, mars):
        grid = harmonize(src, res, cells)
        z = grid.elevation_m
        assert np.nanmedian(tf.slope_degrees(z, grid.resolution_m)) == pytest.approx(math.degrees(math.atan(g)), abs=0.01)
        assert np.nanmax(tf.roughness_rms(z, settings.ROUGHNESS_WINDOW_CELLS)) < 0.05
        span = (settings.RELIEF_WINDOW_CELLS - 1) * res
        assert np.nanmedian(tf.local_relief(z, settings.RELIEF_WINDOW_CELLS)) == pytest.approx(g * span, rel=0.01)


def test_nodata_masks_survive_both_sampling_modes(scenario):
    tmp = scenario["tmp"]
    rng = np.random.default_rng(0)
    e_mask = np.zeros((EARTH_N, EARTH_N), bool)
    e_mask[:500, -500:] = True  # 5 km x 5 km hole, north-east
    e_mask |= rng.random(e_mask.shape) < 0.02  # 2 % scattered dropouts
    m_mask = np.zeros((MARS_N, MARS_N), bool)
    m_mask[-10:, :10] = True  # 5 km x 5 km hole, south-west
    m_mask[30, 30] = True  # one isolated missing pixel
    earth = earth_dem(tmp / "e_nodata.tif", synthetic_surface, e_mask)
    mars = mars_dem(tmp / "m_nodata.tif", synthetic_surface, m_mask)
    res, cells = plan_common_grid(earth, mars)
    e, m = harmonize(earth, res, cells), harmonize(mars, res, cells)
    clean = harmonize(scenario["earth_smooth"], res, cells)
    for g in (e, m):
        assert np.all(np.isfinite(g.elevation_m[g.valid])) and np.all(np.isnan(g.elevation_m[~g.valid]))
        assert np.nanmin(g.elevation_m) > 0  # neither -9999 nor -32768 leaked into any value
    # Aligned Mars: the mask is exactly the source mask, pixel for pixel.
    r0, c0 = find_block(m.elevation_m, read_raw(mars))
    assert np.array_equal(~m.valid, m_mask[r0 : r0 + cells, c0 : c0 + cells])
    # Averaged Earth: holes stay holes; scattered dropouts don't bias valid cells.
    assert not e.valid[:9, -9:].any()
    assert e.valid_fraction == pytest.approx(1 - 25 / 900, abs=0.02)
    hole_edge = np.zeros_like(e.valid)
    hole_edge[:12, -12:] = True  # cells touching the hole are averages of their valid part only
    diff = np.abs(e.elevation_m - clean.elevation_m)
    assert np.nanmax(diff[e.valid & ~hole_edge]) < 0.5
    s = scores(e, m)
    assert all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in s.values())
    assert math.isfinite(similarity.total_similarity(s))


def test_footprint_too_small_for_common_resolution_is_rejected(scenario):
    small = earth_dem(scenario["tmp"] / "small.tif", synthetic_surface, n=1000)  # 10 km -> 19 cells of 500 m
    with pytest.raises(errors.TerraError) as exc:
        plan_common_grid(small, scenario["mars"])
    assert exc.value.code == errors.INSUFFICIENT_EXTENT[0]


# --- Real Gale reference ------------------------------------------------------------------------


@pytest.fixture(scope="module")
def gale():
    ref = load_reference("mars-gale")
    return ref.source, read_raw(ref.source)


@pytest.mark.parametrize("cells", [128, 129])  # 129 is what the 60 km synthetic Earth fixture produces
def test_gale_is_sampled_pixel_for_pixel(gale, cells):
    source, raw = gale
    res = round(source.native_spacing_m, 6)
    assert near_native(source, res)  # 463.06 m N-S, 460.97 m E-W: 0.45 % scale difference
    grid = harmonize(source, res, cells)
    assert grid.sampling == "aligned"
    assert grid.max_offset_m < 0.5 * res
    block = find_block(grid.elevation_m, raw)
    assert block is not None  # every value is an original MOLA pixel; nothing interpolated
    r0, c0 = block
    assert np.array_equal(grid.valid, np.isfinite(raw[r0 : r0 + cells, c0 : c0 + cells]))


def test_gale_full_extent_falls_back_to_averaging(gale):
    """Documented limitation: over ~99 km the 0.45 % E-W mismatch accumulates to half a pixel,
    so a clean 1:1 mapping no longer exists and area averaging is used (with a warning in analyze)."""
    source, _ = gale
    res = round(source.native_spacing_m, 6)
    cells = int(2 * source.half_extent_m // res)
    assert harmonize(source, res, cells).sampling == "average"


def test_gale_zero_valued_nodata_pixels_lie_on_the_zero_metre_contour(gale):
    """Characterizes, does not change, the NoData = 0 convention (see backend/README.md).

    The 7 pixels masked as NoData = 0 all sit where neighbouring elevations change
    sign, which is what genuine 0 m elevations would look like. The source PDS label
    is not in the repository, so the convention is kept until it is checked there.
    """
    source, _ = gale
    with rasterio.open(source.path) as ds:
        raw = ds.read(1)
    zeros = np.argwhere(raw == 0)
    assert len(zeros) == 7
    for r, c in zeros:
        nb = raw[r - 1 : r + 2, c - 1 : c + 2].astype(np.int64)
        nb = nb[nb != 0]
        assert nb.min() < 0 < nb.max()
        assert abs(float(np.median(nb))) < 50
