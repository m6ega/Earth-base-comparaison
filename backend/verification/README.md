# Verification record

Baseline: 110 existing backend tests passed before edits.
Final: 146 tests passed, 0 failed (pytest tests -q -p no:cacheprovider).
Warnings: one existing Starlette/httpx deprecation plus eight expected Rasterio
NotGeoreferencedWarning instances when validating ordinary PNG previews. The
GeoTIFF reference DEMs have verified georeferencing.

acceptance.json records three real HTTP multipart POST /analyze requests to an
isolated Uvicorn instance on 127.0.0.1:8001 using the same synthetic Earth DEM.
All returned HTTP 200 and is_mock=false. Selected DEM hashes, preview bytes,
finite scores and equal Earth/reference grid footprints were checked.
Unsafe path-like reference ID returned 400 UNKNOWN_REFERENCE.
Malformed approval and metadata responses were exercised through FastAPI's
TestClient in the automated suite.

No observational Earth GeoTIFF was found outside the prepared references and raw
lunar products. These acceptance results use a synthetic surface, not real Earth
observations. Gale scores are unchanged from the baseline (total 0.3584422608885516).

protected-hashes.json records pre-edit hashes of the frontend, original reference
assets and raw sources. All were verified unchanged after implementation.
No commit, stage, push or merge was performed. The main branch was unchanged.
