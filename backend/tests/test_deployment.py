"""Production-style behaviour: same-origin frontend delivery and bounded concurrency."""

from __future__ import annotations

import re
import threading

import pytest
from fastapi.testclient import TestClient

import app as app_module
import settings
from app import app

client = TestClient(app)


def test_frontend_served_from_same_origin():
    r = client.get("/")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert "Terra Analog" in r.text


def test_every_local_asset_referenced_by_the_frontend_exists():
    """Guards against broken asset references (e.g. images never committed)."""
    html = (settings.FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    css = (settings.FRONTEND_DIR / "style.css").read_text(encoding="utf-8")
    refs = set(re.findall(r'(?:src|href)="(?![a-zA-Z][a-zA-Z0-9+.-]*:|#)([^"]+)"', html))
    refs |= {m.strip("'\"") for m in re.findall(r"url\(([^)]+)\)", css) if not m.strip("'\"").startswith(("http", "data:", "#"))}
    assert refs, "no local assets found"
    for ref in sorted(refs):
        r = client.get("/" + ref.lstrip("./"))
        assert r.status_code == 200, f"{ref} -> {r.status_code}"


def test_frontend_files_must_be_revalidated_after_deploys():
    for path in ("/", "/script.js", "/style.css", "/config.js"):
        r = client.get(path)
        assert r.headers.get("cache-control") == "no-cache", path
        assert r.headers.get("etag"), path


def test_api_routes_take_precedence_over_static_files():
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/references").json()["is_mock"] is False


def test_static_mount_never_exposes_backend_or_dem_files():
    for path in ("/../backend/settings.py", "/backend/settings.py", "/static/references/mars-gale/dem.tif"):
        assert client.get(path).status_code == 404


def test_config_has_no_fixed_production_api_address():
    config = (settings.FRONTEND_DIR / "config.js").read_text(encoding="utf-8")
    assert "127.0.0.1" not in config and "localhost" not in config


def test_busy_server_returns_503_instead_of_queueing_forever(monkeypatch, synthetic_dem):
    slots = threading.BoundedSemaphore(1)
    slots.acquire()  # all analysis slots occupied
    monkeypatch.setattr(app_module, "_analysis_slots", slots)
    monkeypatch.setattr(settings, "ANALYSIS_QUEUE_TIMEOUT_S", 0)
    with open(synthetic_dem, "rb") as fh:
        r = client.post("/analyze", files={"file": ("earth.tif", fh, "image/tiff")}, data={"reference_id": "mars-gale"})
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "SERVER_BUSY"


def test_slot_released_after_failure(monkeypatch, tmp_path):
    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(app_module, "_analysis_slots", slots)
    bad = tmp_path / "bad.tif"
    bad.write_bytes(b"not a tiff")
    with open(bad, "rb") as fh:
        r = client.post("/analyze", files={"file": ("bad.tif", fh, "image/tiff")}, data={"reference_id": "mars-gale"})
    assert r.status_code == 415
    assert slots.acquire(blocking=False), "analysis slot leaked after an error"


@pytest.mark.parametrize("name,expected", [("TERRA_MAX_CONCURRENT_ANALYSES", 2)])
def test_concurrency_default(name, expected):
    assert settings._env_int(name, expected) >= 1
