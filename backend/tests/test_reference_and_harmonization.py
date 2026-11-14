"""Real Mars Gale reference checks and physical-scale harmonization."""

import json

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

import similarity
import validation
from analysis import compute_features, mars_features
from conftest import ORIGIN, synthetic_surface, utm_grid, write_dem
from preprocessing import harmonize, plan_common_grid
from reference import REFERENCE_DIRS, load_reference
import settings

GALE = REFERENCE_DIRS["mars-gale"]


def test_real_gale_raster_opens_and_matches_metadata():
    meta = json.loads((GALE / "metadata.json").read_text(encoding="utf-8"))
    with rasterio.open(GALE / "dem.tif") as ds:
        band = ds.read(1, masked=True)
        assert (ds.width, ds.height) == (meta["raster"]["width"], meta["raster"]["height"])
        assert ds.res == pytest.approx(tuple(meta["raster"]["resolution_metres"]))
        assert ds.nodata == meta["raster"]["nodata"]
        assert int(band.count()) == meta["raster"]["valid_pixels"]
        assert int(np.ma.count_masked(band)) == meta["raster"]["nodata_pixels"]
        assert float(band.min()) == meta["elevation"]["minimum"]
        assert float(band.max()) == meta["elevation"]["maximum"]
        assert float(band.mean()) == pytest.approx(meta["elevation"]["mean"], rel=1e-9)


def test_reference_loader_verifies_mars_geometry():
    ref = load_reference("mars-gale")
    meta = ref.metadata
    assert ref.source.body == "mars"
    assert ref.source.horizontal_crs.ellipsoid.semi_major_metre == meta["coordinate_system"]["mars_radius_metres"]
    assert ref.source.center_lat == pytest.approx(meta["center"]["latitude_planetocentric"], abs=0.01)
    assert ref.source.center_lon == pytest.approx(meta["center"]["longitude_positive_east"], abs=0.01)
    # Equirectangular with standard parallel 0: east-west ground spacing shrinks by cos(latitude).
    dx, dy = ref.source.spacing_xy_m
    assert dy == pytest.approx(463.0576672, rel=1e-6)
    assert dx == pytest.approx(463.0576672 * np.cos(np.radians(5.4375)), rel=1e-4)
    assert ref.api_object() == {
        "id": "mars-gale",
        "name": meta["region"],
        "dataset": meta["source"],
        "effective_resolution_m": None,
        "preview_url": "/static/references/mars-gale/preview.png",
    }


def test_mars_compared_with_itself_scores_one():
    ref = load_reference("mars-gale")
    res = round(ref.source.native_spacing_m, 6)
    cells = int(2 * ref.source.half_extent_m // res)
    feats = compute_features(harmonize(ref.source, res, cells), "Mars")
    cached = mars_features("mars-gale", res, cells, settings.METHODOLOGY_VERSION)
    scores = {m: similarity.distribution_similarity(feats.histograms[m], cached.histograms[m]) for m in feats.histograms}
    assert all(s == pytest.approx(1.0) for s in scores.values())


def test_common_grid_has_equal_physical_footprint(synthetic_dem):
    earth, _ = validation.open_earth_dem(synthetic_dem)
    mars = load_reference("mars-gale").source
    res, cells = plan_common_grid(earth, mars)
    assert res == pytest.approx(mars.native_spacing_m)  # coarser of the two native spacings
    assert cells * res <= 2 * min(earth.half_extent_m, mars.half_extent_m) + 1e-6
    e = harmonize(earth, res, cells)
    m = harmonize(mars, res, cells)
    assert e.elevation_m.shape == m.elevation_m.shape == (cells, cells)
    assert e.footprint_m == m.footprint_m


def test_resampling_preserves_relief_in_metres(synthetic_dem):
    earth, _ = validation.open_earth_dem(synthetic_dem)
    grid = harmonize(earth, 463.0, 120)
    # Averaging can only shrink extremes; it must not invent elevations beyond the source.
    with rasterio.open(synthetic_dem) as ds:
        src = ds.read(1, masked=True)
    assert float(np.nanmin(grid.elevation_m)) >= float(src.min()) - 1e-3
    assert float(np.nanmax(grid.elevation_m)) <= float(src.max()) + 1e-3
    assert np.nanmax(grid.elevation_m) - np.nanmin(grid.elevation_m) > 0.8 * float(src.max() - src.min())


def test_nodata_does_not_contaminate_resampled_values(tmp_path):
    data = np.full((600, 600), 500.0)
    data[:, :300] = -9999.0  # western half NoData
    path = write_dem(tmp_path / "half.tif", data)
    earth, _ = validation.open_earth_dem(path)
    grid = harmonize(earth, 463.0, 60)
    valid = grid.elevation_m[grid.valid]
    assert np.allclose(valid, 500.0)  # no -9999 bleeding into averages
    assert 0.4 < grid.valid_fraction < 0.6


def test_different_input_resolutions_give_consistent_features(tmp_path):
    """The same analytic surface sampled at 30 m and 90 m harmonizes to nearly the same grid."""
    paths = {}
    for pixel in (30.0, 90.0):
        size = int(60_000 / pixel)
        x, y = utm_grid(size, pixel)
        paths[pixel] = write_dem(
            tmp_path / f"s{int(pixel)}.tif", synthetic_surface(x, y), transform=from_origin(*ORIGIN, pixel, pixel)
        )
    grids, feats = {}, {}
    for pixel, path in paths.items():
        src, _ = validation.open_earth_dem(path)
        grids[pixel] = harmonize(src, 463.0, 120)
        feats[pixel] = compute_features(grids[pixel], "Earth")
    diff = np.nanmean(np.abs(grids[30.0].elevation_m - grids[90.0].elevation_m))
    assert diff < 5.0  # metres, against ~1 km of relief
    for m in feats[30.0].histograms:
        assert similarity.distribution_similarity(feats[30.0].histograms[m], feats[90.0].histograms[m]) > 0.9
