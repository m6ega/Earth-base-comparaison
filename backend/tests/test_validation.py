"""Upload validation on synthetic GeoTIFFs (not real observations)."""

import io

import numpy as np
import pytest
from rasterio.transform import from_origin

import errors
import settings
import validation
from analysis import analyze
from conftest import synthetic_surface, utm_grid, write_dem

MARS_WKT = (
    'PROJCS["Mars_simpCyl_c180",GEOGCS["GCS_Mars",DATUM["D_Mars",SPHEROID["Mars",3396000,0]],'
    'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],PROJECTION["Equirectangular"],'
    'PARAMETER["standard_parallel_1",0],PARAMETER["central_meridian",180],PARAMETER["false_easting",0],'
    'PARAMETER["false_northing",0],UNIT["metre",1]]'
)


def code_of(excinfo):
    return excinfo.value.code


def test_valid_synthetic_dem(synthetic_dem):
    source, facts = validation.open_earth_dem(synthetic_dem)
    assert source.body == "earth"
    assert facts["vertical_to_metres"] == 1.0
    # UTM grid scale factor away from the central meridian makes ground spacing differ slightly from 50 m.
    assert source.native_spacing_m == pytest.approx(50.0, rel=0.002)
    # Meridian convergence rotates the UTM grid against true north, so the largest
    # true-north-aligned centred square is slightly smaller than the 60 km raster.
    assert 0.99 * 30_000.0 < source.half_extent_m <= 30_000.0


def test_geographic_pixel_spacing_is_physical_not_degrees(tmp_path):
    # 0.001 degree pixels centred on the equator: ~111.32 m east-west, ~110.57 m north-south.
    data = np.full((200, 200), 100.0)
    path = write_dem(tmp_path / "geo.tif", data, crs="EPSG:4326", transform=from_origin(20.0, 0.1, 0.001, 0.001))
    source, _ = validation.open_earth_dem(path)
    dx, dy = source.spacing_xy_m
    assert dx == pytest.approx(111.32, abs=0.05)
    assert dy == pytest.approx(110.57, abs=0.05)


def test_invalid_tiff_bytes(tmp_path):
    path = tmp_path / "broken.tif"
    path.write_bytes(b"II*\x00" + b"\x13\x37" * 500)
    with pytest.raises(errors.TerraError) as e:
        validation.open_earth_dem(path)
    assert code_of(e) == "INVALID_DEM"


def test_non_tiff_content_with_tif_extension(tmp_path):
    path = tmp_path / "image.tif"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    with pytest.raises(errors.TerraError) as e:
        validation.open_earth_dem(path)
    assert code_of(e) == "UNSUPPORTED_FORMAT"


@pytest.mark.parametrize("name", ["dem.png", "dem.tif.zip", "", None, "dem"])
def test_wrong_extension(name):
    with pytest.raises(errors.TerraError) as e:
        validation.check_extension(name)
    assert code_of(e) == "UNSUPPORTED_FORMAT"


@pytest.mark.parametrize("name", ["dem.tif", "DEM.TIFF", "a.b.tiff"])
def test_accepted_extension(name):
    validation.check_extension(name)


def test_missing_crs(tmp_path):
    path = write_dem(tmp_path / "nocrs.tif", np.ones((100, 100)), crs=None)
    with pytest.raises(errors.TerraError) as e:
        validation.open_earth_dem(path)
    assert code_of(e) == "MISSING_CRS"


def test_missing_vertical_units(tmp_path):
    path = write_dem(tmp_path / "nounits.tif", np.ones((100, 100)), units=None)
    with pytest.raises(errors.TerraError) as e:
        validation.open_earth_dem(path)
    assert code_of(e) == "UNKNOWN_VERTICAL_UNITS"


def test_unsupported_vertical_unit(tmp_path):
    path = write_dem(tmp_path / "cm.tif", np.ones((100, 100)), units="centimetre")
    with pytest.raises(errors.TerraError) as e:
        validation.open_earth_dem(path)
    assert code_of(e) == "UNKNOWN_VERTICAL_UNITS"


def test_feet_are_converted(tmp_path):
    path = write_dem(tmp_path / "ft.tif", np.ones((100, 100)), units="ft")
    _, facts = validation.open_earth_dem(path)
    assert facts["vertical_to_metres"] == pytest.approx(0.3048)


def test_multiband_rejected(tmp_path):
    path = write_dem(tmp_path / "rgb.tif", np.ones((50, 50)), count=3)
    with pytest.raises(errors.TerraError) as e:
        validation.open_earth_dem(path)
    assert code_of(e) == "INVALID_DEM"


def test_mars_crs_upload_rejected(tmp_path):
    path = write_dem(tmp_path / "mars.tif", np.ones((50, 50)), crs=MARS_WKT, transform=from_origin(-2.5e6, -2.7e5, 463, 463))
    with pytest.raises(errors.TerraError) as e:
        validation.open_earth_dem(path)
    assert code_of(e) == "UNSUPPORTED_CRS"


def test_header_pixel_limit(tmp_path, monkeypatch):
    path = write_dem(tmp_path / "big.tif", np.ones((100, 100)))
    monkeypatch.setattr(settings, "MAX_RASTER_PIXELS", 5_000)
    with pytest.raises(errors.TerraError) as e:
        validation.open_earth_dem(path)
    assert code_of(e) == "RASTER_TOO_LARGE" and e.value.http_status == 413


def test_upload_size_limit_enforced_while_copying(tmp_path):
    stream = io.BytesIO(b"\0" * (settings.MAX_UPLOAD_BYTES + 1))
    with pytest.raises(errors.TerraError) as e:
        validation.save_upload(stream, tmp_path / "upload.tif")
    assert code_of(e) == "FILE_TOO_LARGE" and e.value.http_status == 413


def test_empty_upload(tmp_path):
    with pytest.raises(errors.TerraError) as e:
        validation.save_upload(io.BytesIO(b""), tmp_path / "upload.tif")
    assert code_of(e) == "INVALID_DEM"


def _surface(size=1200, pixel=50.0):
    x, y = utm_grid(size, pixel)
    return synthetic_surface(x, y)


def test_too_many_invalid_pixels(tmp_path):
    data = _surface()
    data[:, : int(0.7 * data.shape[1])] = -9999.0  # 70 % NoData
    path = write_dem(tmp_path / "sparse.tif", data)
    with pytest.raises(errors.TerraError) as e:
        analyze(path, "mars-gale")
    assert code_of(e) == "INSUFFICIENT_VALID_DATA"


def test_fully_masked_raster(tmp_path):
    path = write_dem(tmp_path / "empty.tif", np.full((1200, 1200), -9999.0))
    with pytest.raises(errors.TerraError) as e:
        analyze(path, "mars-gale")
    assert code_of(e) == "INSUFFICIENT_VALID_DATA"


def test_nan_values_are_treated_as_invalid(tmp_path):
    data = _surface()
    data[:, :900] = np.nan  # 75 % non-finite, no declared NoData needed
    path = write_dem(tmp_path / "nan.tif", data, nodata=None)
    with pytest.raises(errors.TerraError) as e:
        analyze(path, "mars-gale")
    assert code_of(e) == "INSUFFICIENT_VALID_DATA"


def test_valid_partial_nodata_produces_result_with_warning(tmp_path):
    data = _surface()
    data[:300, :600] = -9999.0  # 12.5 % NoData
    path = write_dem(tmp_path / "partial.tif", data)
    result = analyze(path, "mars-gale")
    codes = {w["code"] for w in result["warnings"]}
    assert "PARTIAL_COVERAGE" in codes
    assert 0.0 <= result["total_similarity"] <= 1.0


def test_undeclared_nodata_sentinel_is_rejected(tmp_path):
    data = _surface()
    data[:100, :100] = -32768.0  # sentinel not declared as NoData
    path = write_dem(tmp_path / "sentinel.tif", data, nodata=None)
    with pytest.raises(errors.TerraError) as e:
        analyze(path, "mars-gale")
    assert code_of(e) == "INVALID_DEM"


def test_too_small_footprint(tmp_path):
    path = write_dem(tmp_path / "tiny.tif", _surface(size=200, pixel=50.0))  # 10 km
    with pytest.raises(errors.TerraError) as e:
        analyze(path, "mars-gale")
    assert code_of(e) == "INSUFFICIENT_EXTENT"
