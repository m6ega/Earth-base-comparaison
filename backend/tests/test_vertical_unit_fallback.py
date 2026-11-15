"""Optional vertical_unit_fallback: a default for files that declare no units.

The fallback must never override declared metadata or an explicit selection,
so declared feet are always converted and never read as metres.
"""

from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

import errors
import validation
from app import app
from conftest import synthetic_surface, write_dem

client = TestClient(app)


def _dem(tmp_path, name, units, scale=None, offset=None):
    y, x = np.mgrid[0:1200, 0:1200] * 50.0
    data = synthetic_surface(x, -y).astype("float32")
    path = write_dem(tmp_path / name, data, units=units)
    if scale is not None:
        import rasterio
        with rasterio.open(path, "r+") as ds:
            ds.scales = (scale,)
            ds.offsets = (offset,)
    return path


def _post(path, **form):
    with open(path, "rb") as fh:
        return client.post(
            "/analyze",
            files={"file": ("earth.tif", fh, "image/tiff")},
            data={"reference_id": "mars-gale", **form},
        )


def _codes(resp):
    return {w["code"] for w in resp.json()["warnings"]}


# ---- validation layer -------------------------------------------------------

def test_fallback_used_only_when_no_units_declared(tmp_path):
    path = write_dem(tmp_path / "none.tif", np.ones((100, 100)), units=None)
    _, facts = validation.open_earth_dem(path, vertical_unit_fallback="metre")
    assert facts["vertical_to_metres"] == 1.0
    assert facts["vertical_unit_source"] == validation.ASSUMED_UNIT_SOURCE


@pytest.mark.parametrize("fallback", ["metre", "foot"])
def test_declared_feet_never_overridden_by_fallback(tmp_path, fallback):
    path = write_dem(tmp_path / "ft.tif", np.ones((100, 100)), units="ft")
    _, facts = validation.open_earth_dem(path, vertical_unit_fallback=fallback)
    assert facts["vertical_to_metres"] == pytest.approx(0.3048)
    assert facts["vertical_unit_source"] == "band unit"


def test_declared_metres_never_overridden_by_fallback(tmp_path):
    path = write_dem(tmp_path / "m.tif", np.ones((100, 100)), units="metre")
    _, facts = validation.open_earth_dem(path, vertical_unit_fallback="foot")
    assert facts["vertical_to_metres"] == 1.0
    assert facts["vertical_unit_source"] == "band unit"


def test_explicit_selection_wins_over_fallback(tmp_path):
    path = write_dem(tmp_path / "none.tif", np.ones((100, 100)), units=None)
    _, facts = validation.open_earth_dem(path, vertical_unit="foot", vertical_unit_fallback="metre")
    assert facts["vertical_to_metres"] == pytest.approx(0.3048)
    assert facts["vertical_unit_source"] == "user selection"


def test_unsupported_declared_unit_still_rejected_with_fallback(tmp_path):
    path = write_dem(tmp_path / "cm.tif", np.ones((100, 100)), units="centimetre")
    with pytest.raises(errors.TerraError) as exc:
        validation.open_earth_dem(path, vertical_unit_fallback="metre")
    assert exc.value.code == "UNKNOWN_VERTICAL_UNITS"


def test_no_fallback_keeps_strict_behaviour(tmp_path):
    path = write_dem(tmp_path / "none.tif", np.ones((100, 100)), units=None)
    with pytest.raises(errors.TerraError) as exc:
        validation.open_earth_dem(path)
    assert exc.value.code == "UNKNOWN_VERTICAL_UNITS"


# ---- API layer --------------------------------------------------------------

def test_api_undeclared_units_single_request_with_disclosure(tmp_path):
    r = _post(_dem(tmp_path, "none.tif", None), vertical_unit_fallback="metre")
    assert r.status_code == 200, r.text
    assert "VERTICAL_UNITS_ASSUMED" in _codes(r)
    assert "VERTICAL_UNITS_CONVERTED" not in _codes(r)


def test_api_undeclared_metre_fallback_equals_explicit_metres(tmp_path):
    path = _dem(tmp_path, "none.tif", None)
    a = _post(path, vertical_unit_fallback="metre").json()
    b = _post(path, vertical_unit="metre").json()
    assert a["total_similarity"] == b["total_similarity"]
    assert a["scores"] == b["scores"]


def test_api_declared_feet_converted_not_assumed(tmp_path):
    r = _post(_dem(tmp_path, "ft.tif", "ft"), vertical_unit_fallback="metre")
    assert r.status_code == 200, r.text
    assert "VERTICAL_UNITS_CONVERTED" in _codes(r)
    assert "VERTICAL_UNITS_ASSUMED" not in _codes(r)


def test_api_declared_metres_unchanged_by_fallback(tmp_path):
    path = _dem(tmp_path, "m.tif", "metre")
    with_fallback = _post(path, vertical_unit_fallback="foot").json()
    without = _post(path).json()
    assert with_fallback["scores"] == without["scores"]
    assert not {"VERTICAL_UNITS_ASSUMED", "VERTICAL_UNITS_CONVERTED"} & _codes(_post(path, vertical_unit_fallback="foot"))


def test_api_scale_offset_still_decoded_with_fallback(tmp_path):
    r = _post(_dem(tmp_path, "scaled.tif", None, scale=1.0, offset=10.0), vertical_unit_fallback="metre")
    assert r.status_code == 200, r.text
    assert {"VERTICAL_UNITS_ASSUMED", "ELEVATION_ENCODING_APPLIED"} <= _codes(r)


def test_api_rejects_unsupported_fallback(tmp_path):
    r = _post(_dem(tmp_path, "none.tif", None), vertical_unit_fallback="furlong")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "UNKNOWN_VERTICAL_UNITS"


def test_api_without_fallback_unchanged(tmp_path):
    r = _post(_dem(tmp_path, "none.tif", None))
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "UNKNOWN_VERTICAL_UNITS"
