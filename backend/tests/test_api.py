"""API integration tests. The Earth DEMs used here are SYNTHETIC."""

import base64
import json
import math

import pytest
from fastapi.testclient import TestClient

import settings
from app import app

client = TestClient(app)


def assert_contract_success(body: dict) -> None:
    """Check the POST /analyze success shape from docs/api-contract.md."""
    assert set(body) == {
        "status", "is_mock", "reference", "total_similarity", "scores", "earth_preview_url", "charts", "warnings",
    }
    assert body["status"] == "success" and body["is_mock"] is False
    ref = body["reference"]
    assert set(ref) == {"id", "name", "dataset", "effective_resolution_m", "preview_url"}
    assert isinstance(ref["id"], str) and isinstance(ref["name"], str) and isinstance(ref["dataset"], str)
    assert ref["effective_resolution_m"] is None or isinstance(ref["effective_resolution_m"], (int, float))
    assert set(body["scores"]) == {"relative_relief", "slope_distribution", "surface_roughness"}
    for v in [body["total_similarity"], *body["scores"].values()]:
        assert isinstance(v, float) and math.isfinite(v) and 0.0 <= v <= 1.0
    chart = body["charts"]["slope_distribution"]
    assert set(body["charts"]) == {"slope_distribution"}
    assert set(chart) == {"unit", "bin_edges", "earth", "mars"}
    assert chart["unit"] == "degrees"
    n = len(chart["bin_edges"]) - 1
    assert len(chart["earth"]) == n and len(chart["mars"]) == n
    assert all(b > a for a, b in zip(chart["bin_edges"], chart["bin_edges"][1:]))
    assert sum(chart["earth"]) == pytest.approx(1.0) and sum(chart["mars"]) == pytest.approx(1.0)
    assert body["earth_preview_url"].startswith("data:image/png;base64,")
    png = base64.b64decode(body["earth_preview_url"].split(",", 1)[1])
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    for w in body["warnings"]:
        assert set(w) == {"code", "message"} and w["code"] and w["message"]


def assert_error(resp, status: int, code: str) -> None:
    assert resp.status_code == status, resp.text
    body = resp.json()
    assert body["status"] == "error" and body["error"]["code"] == code and body["error"]["message"]


def post_file(path, name="earth.tif", reference_id="mars-gale"):
    with open(path, "rb") as fh:
        return client.post("/analyze", files={"file": (name, fh, "image/tiff")}, data={"reference_id": reference_id})


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_references():
    r = client.get("/references")
    assert r.status_code == 200
    body = r.json()
    assert body["is_mock"] is False
    assert [ref["id"] for ref in body["references"]] == ["mars-gale"]
    assert body["references"][0]["preview_url"] == "/static/references/mars-gale/preview.png"


def test_reference_preview_served_but_not_dem():
    r = client.get("/static/references/mars-gale/preview.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.content[:4] == b"\x89PNG"
    assert client.get("/static/references/mars-gale/dem.tif").status_code == 404
    assert_error(client.get("/static/references/..%2F..%2Fsettings/preview.png"), 404, "NOT_FOUND")


def test_analyze_success_with_synthetic_dem(synthetic_dem):
    r = post_file(synthetic_dem)
    assert r.status_code == 200, r.text
    body = r.json()
    assert_contract_success(body)
    json.dumps(body, allow_nan=False)
    scores = body["scores"]
    w = settings.SCORE_WEIGHTS
    assert body["total_similarity"] == pytest.approx(sum(w[k] * scores[k] for k in w))
    codes = {x["code"] for x in body["warnings"]}
    assert {"METHODOLOGY_PROVISIONAL", "COMPARISON_SCALE", "RESOLUTION_REDUCED", "FOOTPRINT_LIMITED_BY_EARTH"} <= codes
    # A synthetic surface is not Gale Crater: scores must be computed, not saturated.
    assert body["total_similarity"] < 0.999


def test_analyze_is_reproducible(synthetic_dem):
    a, b = post_file(synthetic_dem).json(), post_file(synthetic_dem).json()
    assert a == b


def test_flat_terrain_is_valid_but_flagged(tmp_path):
    import numpy as np
    from conftest import write_dem

    path = write_dem(tmp_path / "flat.tif", np.full((1200, 1200), 250.0))
    r = post_file(path)
    assert r.status_code == 200, r.text
    body = r.json()
    assert_contract_success(body)
    assert "FLAT_TERRAIN" in {w["code"] for w in body["warnings"]}
    # A flat plain against a crater: slope similarity must be low.
    assert body["scores"]["slope_distribution"] < 0.6


def test_unknown_reference(synthetic_dem):
    assert_error(post_file(synthetic_dem, reference_id="mars-gusev"), 400, "UNKNOWN_REFERENCE")
    assert_error(post_file(synthetic_dem, reference_id="../references/mars-gale"), 400, "UNKNOWN_REFERENCE")


def test_missing_fields(synthetic_dem):
    assert_error(client.post("/analyze", data={"reference_id": "mars-gale"}), 422, "MISSING_FIELD")
    with open(synthetic_dem, "rb") as fh:
        assert_error(client.post("/analyze", files={"file": ("e.tif", fh)}), 422, "MISSING_FIELD")


def test_invalid_tiff_upload(tmp_path):
    p = tmp_path / "bad.tif"
    p.write_bytes(b"II*\x00garbage" * 10)
    assert_error(post_file(p), 422, "INVALID_DEM")


def test_wrong_extension_upload(synthetic_dem):
    assert_error(post_file(synthetic_dem, name="earth.png"), 415, "UNSUPPORTED_FORMAT")


def test_missing_crs_upload(tmp_path):
    import numpy as np
    from conftest import write_dem

    assert_error(post_file(write_dem(tmp_path / "n.tif", np.ones((50, 50)), crs=None)), 422, "MISSING_CRS")


def test_oversized_upload_with_content_length():
    payload = b"\0" * (settings.MAX_UPLOAD_BYTES + 2 * 1024 * 1024)
    r = client.post("/analyze", files={"file": ("big.tif", payload)}, data={"reference_id": "mars-gale"})
    assert_error(r, 413, "FILE_TOO_LARGE")


def test_oversized_streamed_upload_without_content_length():
    boundary = "terraboundary"
    head = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"reference_id\"\r\n\r\nmars-gale\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"big.tif\"\r\n"
        "Content-Type: image/tiff\r\n\r\n"
    ).encode()

    def body():
        yield head
        chunk = b"\0" * (1024 * 1024)
        for _ in range(53):
            yield chunk
        yield f"\r\n--{boundary}--\r\n".encode()

    r = client.post(
        "/analyze", content=body(), headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    assert "content-length" not in {k.lower() for k in r.request.headers}
    assert_error(r, 413, "FILE_TOO_LARGE")


def test_cors_allows_local_frontend_only():
    ok = client.options(
        "/analyze", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"}
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-credentials" not in ok.headers
    bad = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in bad.headers


def test_unknown_route_uses_error_shape():
    assert_error(client.get("/nope"), 404, "NOT_FOUND")
