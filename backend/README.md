# Backend

**Status:** Phase 1 terrain comparison engine implemented on `backend--dev`, pending human review. The scientific method below is a **proposal**: [docs/methodology.md](../docs/methodology.md) has not approved any formula, threshold or weight.

**Owner:** Backend Lead + Claude, on `backend--dev`. Scope, stack and responsibilities: [PROJECT-CONTEXT.md](../PROJECT-CONTEXT.md).

The backend implements the three MVP endpoints in the [API contract](../docs/api-contract.md). Every score is computed from real raster data. Responses always have `is_mock: false`.

## Mars reference storage

The backend owns the Mars DEM and reference metadata:

```text
backend/references/mars-gale/
  dem.tif         validated numerical Mars elevation GeoTIFF
  preview.png     prepared Mars terrain visualization
  metadata.json   verified source and geospatial metadata
```

Reference ID: `mars-gale`. The backend serves `preview.png` to the frontend, which does not store or analyze the Mars DEM. Source provenance comes from `metadata.json`. Git tracking policy: [data/README.md](../data/README.md#storage).

On first use, `reference.py` cross-checks `dem.tif` against `metadata.json`: size, pixel spacing, NoData, Mars sphere radius, vertical units and centre. If any check fails, the backend returns `REFERENCE_UNAVAILABLE` and computes no scores.

## Code layout

| File | Role |
| --- | --- |
| `app.py` | FastAPI routes, upload size limit middleware, CORS and error handlers |
| `analysis.py` | The pipeline (validate, harmonize, features, similarity, preview, response), independent of FastAPI |
| `validation.py` | Upload saving and strict GeoTIFF validation |
| `reference.py` | Mars reference loading and integrity checks |
| `preprocessing.py` | Planet-specific local projections, footprint planning and mask-preserving resampling |
| `terrain_features.py` | Pure NumPy terrain mathematics |
| `similarity.py` | Jensen–Shannon similarity and weighted total |
| `preview.py` | Earth hillshade preview as an inline PNG |
| `settings.py` | Every threshold, bin edge, weight and limit, plus `METHODOLOGY_VERSION` |
| `errors.py` | Error codes and HTTP statuses |
| `tests/` | pytest suite using **synthetic** GeoTIFFs and the real Gale reference |

The application entry point is `app.py`. The empty `backend/main.py` placeholder is not used.

## Setup and run (Windows PowerShell)

Run all commands from the repository root.

Use Python 3.14 (the validated environment). For runtime only, install
`requirements.txt`; it includes `pyproj` for CRS validation and projections.
For development and tests, `requirements-dev.txt` includes all runtime dependencies.

```powershell
cd backend
python -m venv .venv          # skip if .venv already exists
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

In another terminal at the repository root, serve the existing static frontend:

```powershell
python -m http.server 5500 --bind 127.0.0.1 --directory frontend
```

Open http://127.0.0.1:5500. `frontend/config.js` defaults to the backend at
http://127.0.0.1:8000. Select an Earth GeoTIFF and click **Analyze Terrain**.
The development and testing branch is `frontend--dev`; `main` is stable production.

Test the API from a second PowerShell window. `curl.exe` is built into Windows 10 and later. Replace the path with your own GeoTIFF.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/references | ConvertTo-Json -Depth 5
curl.exe -s -F "file=@C:\path\to\earth_dem.tif" -F "reference_id=mars-gale" http://127.0.0.1:8000/analyze
```

To create a **synthetic** test DEM (not a real observation), run this in `backend` with the venv active:

```powershell
python -c "import sys; sys.path.insert(0,'tests'); from conftest import *; from pathlib import Path; x,y=utm_grid(1200,50.0); write_dem(Path('synthetic_earth.tif'), synthetic_surface(x,y))"
curl.exe -s -F "file=@synthetic_earth.tif" -F "reference_id=mars-gale" http://127.0.0.1:8000/analyze
Remove-Item synthetic_earth.tif
```

CORS allows the local Vite (`5173`, `4173`) and Live Server (`5500`) origins on `localhost` and `127.0.0.1`, without credentials. To override, set a comma-separated list before starting the server, for example `$env:TERRA_CORS_ORIGINS = "http://localhost:3000"`. Wildcards are ignored.

## Scientific method (proposal, methodology version `0.2-proposal`)

### Validation (hard failures)

An upload is rejected unless all of these hold:

- **File:** a `.tif`/`.tiff` name, TIFF magic bytes, and GDAL's GTiff driver.
- **Upload size:** at most 50 MB. The middleware checks `Content-Length` and also counts streamed bytes, and the file copy is checked again.
- **Dimensions:** at most 200 million declared pixels, and at most 40 million decoded pixels in the comparison window.
- **Band and type:** exactly one band of an integer or float type.
- **Georeferencing:** an affine geotransform (GCP-only files are rejected) and a geographic or projected CRS on an **Earth** ellipsoid (semi-major axis 6,350–6,400 km).
- **Vertical units:** declared by the band unit or a vertical CRS, in metres or feet. Feet are converted. Units are never assumed.
- **Elevations:** valid values within −12,000 to 9,000 m, which catches wrong units and undeclared NoData sentinels.

### Harmonization: equal ground footprint and common resolution

1. Each DEM gets its own **local azimuthal equidistant projection** on its own body: the Earth ellipsoid for uploads, and the 3,396,000 m Mars sphere from the reference CRS. It is centred on the raster centre. Earth geodesy is never applied to Mars, and degrees are never treated as metres.
2. **Native spacing:** the true ground distance between neighbouring pixels at the centre, taking the larger axis. For Gale this is 463.06 m north–south and 460.97 m east–west.
3. **Common resolution:** `r = max(earth_spacing, mars_spacing)`. No DEM is resampled to finer than its source.
4. **Footprint:** the largest centred square that fits inside both rasters, `n = floor(2·min(h_earth, h_mars) / r)` cells per side.
   - Both grids are `n × n` cells of `r` metres, so they cover identical ground size and are never stretched.
   - The comparison is rejected if `n < 32` (`INSUFFICIENT_EXTENT`).
5. **Resampling of a finer DEM:** area-weighted average (GDAL `average`) of valid pixels only. NoData never enters an average. A separate coverage raster marks a cell valid only if valid source pixels cover at least 50% of it.
6. **Sampling of a DEM already at the common resolution** (spacing within 1% of `r` on both axes, `ALIGNED_MAX_SCALE_ERROR`; normally the Mars reference): no averaging.
   - The grid is shifted by less than one cell so that cell centres fall on source pixel centres. Each cell then takes exactly one source pixel, and its NoData mask is the source mask.
   - It is used only if the mapping is verified to be a one-to-one re-indexing of a contiguous pixel block. Otherwise the DEM is area-averaged and the result carries `NEAR_NATIVE_INTERPOLATED`.
   - Why: until version 0.1, averaging at a ~1:1 ratio onto a grid offset from the pixels blended up to 2 × 2 pixels. That smoothed only the coarser DEM. On a synthetic 30 km test, Mars roughness fell by 40%. On Gale, median roughness fell by 20%. The effect depended on whether the cell count was odd or even.
   - Cost: the 0.45% east–west spacing difference of Gale (460.97 m pixels in 463.06 m cells) is accepted as a scale error. Positional error is at most 160 m (0.34 cell) on the 129-cell grid. Over the full ~99 km Gale extent the drift reaches half a pixel, so that case falls back to averaging.

The footprint and resolution are reported in the `COMPARISON_SCALE` warning of each result.

### NoData policy

- Declared NoData and non-finite values are masked.
- Below 50% valid cells in the Earth window, the upload is rejected (`INSUFFICIENT_VALID_DATA`). Below 95%, the result carries a `PARTIAL_COVERAGE` warning.
- Each feature uses only complete neighbourhoods (every cell valid) and needs at least 256 of them.

### Features (on the harmonized grid, cell size `r`)

| Metric | Definition | Histogram bins (shared by Earth and Mars) |
| --- | --- | --- |
| Relative relief | Local relief: `max(z) − min(z)` in a 5 × 5-cell window, in metres. Datum-independent, and keeps the amplitude in metres. | 0, 5, 10, 20, 40, 80, 160, 320, 640, 1280, 2560, 10000 m |
| Slope distribution | Horn (1981) 3 × 3 gradient: `slope = atan(√((dz/dx)² + (dz/dy)²))` in degrees, with `dz/dx = ((c+2f+i) − (a+2d+g)) / 8r` | 0, 1, 2, 3, 5, 7.5, 10, 15, 20, 30, 45, 90° |
| Surface roughness | RMS residual after a least-squares plane fit in a 3 × 3-cell window, in metres. A plane of any slope has zero roughness. | 0, 0.5, 1, 2, 4, 8, 16, 32, 64, 128, 256, 10000 m |

Values above the last edge count in the last bin.

### Similarity

- **Per metric:** `score = 1 − JSD₂(p_earth, p_mars)`, where `JSD₂` is the base-2 Jensen–Shannon *distance* (the square root of the divergence). It lies in [0, 1], so the score does too.
- **Total:** `total_similarity = (relative_relief + slope_distribution + surface_roughness) / 3`. These are equal weights, which is a proposal with no scientific claim.
- **Score scale:** the contract specifies 0–1, and the frontend displays percentages. `100 × (1 − distance)` is the same number shown as a percentage.
- **Numerical checks:** distributions must be finite, non-negative and have mass. Scores must be finite and within [0, 1]. Responses are serialized with `allow_nan=False`. Any failure returns `PROCESSING_FAILED`, never a default score.
- **Mars feature cache:** in memory (LRU), keyed by reference ID, resolution, cell count and `METHODOLOGY_VERSION`.
- **What the score is not:** it is not a probability, a confidence or a statistical test. It is a bounded distance between two histograms: 1 means identical histograms, and 0 means no shared bins. It is not calibrated against any terrain-analog judgement and says nothing about site suitability.
  - Neighbourhoods overlap, so histogram counts are not independent samples.
  - Finite grids from the same terrain process score below 1.
  - Values exactly on a bin edge can be split between two bins by rounding.
  - Flat terrain on both sides scores 1.0 on every metric, a degenerate result that is flagged only for Earth (`FLAT_TERRAIN`).

### Warnings (proposed codes)

| Code | When it appears |
| --- | --- |
| `METHODOLOGY_PROVISIONAL` | Always |
| `COMPARISON_SCALE` | Always: reports the footprint and resolution |
| `EFFECTIVE_RESOLUTION_UNVERIFIED` | The reference's `effective_resolution_m` is `null` (currently always for Gale) |
| `NEAR_NATIVE_INTERPOLATED` | A DEM at the common resolution could not be sampled pixel-for-pixel and was averaged at ~1:1 |
| `RESOLUTION_REDUCED` | The Earth DEM is finer than Mars |
| `EARTH_COARSER_THAN_REFERENCE` | The Earth DEM is coarser than Mars |
| `FOOTPRINT_LIMITED_BY_EARTH` | The Earth DEM is smaller than the Mars reference |
| `PARTIAL_COVERAGE` | 50–95% of the Earth window is valid |
| `VERTICAL_UNITS_CONVERTED` | Elevations were converted from feet |
| `FLAT_TERRAIN` | The local relief everywhere is below 1 m |

### Errors (proposed codes)

| Status | Codes |
| --- | --- |
| 400 | `UNKNOWN_REFERENCE`, `INVALID_REQUEST` (malformed `Content-Length`) |
| 413 | `FILE_TOO_LARGE`, `RASTER_TOO_LARGE` |
| 415 | `UNSUPPORTED_FORMAT` |
| 422 | `MISSING_FIELD`, `INVALID_REQUEST`, `INVALID_DEM`, `MISSING_CRS`, `UNSUPPORTED_CRS`, `UNKNOWN_VERTICAL_UNITS`, `INSUFFICIENT_EXTENT`, `INSUFFICIENT_VALID_DATA` |
| 500 | `REFERENCE_UNAVAILABLE`, `PROCESSING_FAILED` |

Every error uses the contract's error shape and never exposes paths or stack traces.

### Assumptions and limitations

- **Unapproved choices:** all thresholds, windows, bins and weights are proposals. Scores are uncalibrated and describe geometry only, not habitability or suitability.
- **Resolution:** at the common resolution of about 463 m, features describe kilometre-scale terrain. Finer Earth detail is deliberately discarded.
- **MOLA data quality:**
  - MEGDR cells are partly interpolated where tracks are absent (see `metadata.json`), so the effective Mars resolution may be coarser than 463 m in places.
  - `effective_resolution_m` stays `null` until verified, and every result carries `EFFECTIVE_RESOLUTION_UNVERIFIED`. Expected direction of the bias: Mars slope and roughness are underestimated relative to Earth. Its size is unknown.
  - Zero is treated as NoData, per the source header, even though 0 m is a possible Mars elevation.
    - **Unresolved; the data are unchanged.** All 7 masked pixels sit on the 0 m contour: their neighbours are small values of both signs. They look like genuine elevations rather than gaps.
    - The source label `megt00n090hb.xml` is not in the repository, so the convention cannot be confirmed or rejected here.
    - Impact against the synthetic Earth: treating them as valid changes the total from 0.3584 to 0.3594.
    - `tests/test_scale_harmonization.py` records this finding.
- **Support mismatch:** an Earth cell is a box average of finer data. A Mars cell is one MOLA grid value with its own, undocumented footprint. Even identical landscapes do not score 1.0: 0.88 total in the synthetic 30 km test, where Mars values are point samples.
- **Windowing:** the central window is deterministic. A NoData-heavy centre can cause rejection even if valid terrain exists elsewhere.
- **Earth datum:** the local Earth projection uses the upload's own geodetic CRS. Vertical datums do not matter because no absolute elevations are compared.
- **Caching:** the cache is per process and not persisted.

### Before using real Earth satellite DEMs

- Confirm that real products declare vertical units. Many SRTM, Copernicus and ASTER GeoTIFFs do not. Units may only be added after checking the product documentation (`gdal_edit.py -units metre file.tif`).
- Test with representative real DEMs in geographic and projected CRSs, and check the plausibility thresholds and the 32-cell minimum footprint.
- Have humans review and approve the bin edges, windows, weights and warning and error codes, then record them in `docs/methodology.md` and `docs/api-contract.md`.
