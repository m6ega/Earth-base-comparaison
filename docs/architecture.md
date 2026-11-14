# Architecture plan

Approved scope, stack and data ownership: [PROJECT-CONTEXT.md](../PROJECT-CONTEXT.md). Endpoints and response schema: [API contract](api-contract.md). This document describes how the parts fit together. Nothing here is implemented yet.

## Components

| Component | Technology | Role |
| --- | --- | --- |
| Frontend | React + Vite | Reference selection, upload, previews, scores, slope chart, warnings and errors. No scientific calculations. |
| Backend API | Python + FastAPI | `GET /health`, `GET /references`, `POST /analyze`; validation and error handling |
| Processing | Rasterio + NumPy (SciPy optional) | DEM reading, preprocessing, metric extraction, scoring, preview rendering |
| Reference store | Backend-side files under `backend/references/` | Prepared Mars MOLA GeoTIFFs, previews, metadata and (later) cached Mars features. Large rasters stay outside Git; see [data/README.md](../data/README.md#storage). |

## Planned flow

```text
Reference preparation (offline, backend)
  MOLA source -> validate -> prepare reference GeoTIFF
              -> render Mars preview PNG
              -> precompute and cache Mars features

Request flow
  React: GET /references -> show Gale Crater (and Gusev once prepared)
  React: upload Earth GeoTIFF + reference_id -> POST /analyze
  FastAPI: validate file and reference_id
         -> load cached Mars features (recompute if stale)
         -> preprocess Earth DEM to the agreed processing scale
         -> extract relief, slope distribution, roughness
         -> per-metric scores + total_similarity (0-1)
         -> render Earth preview; build slope chart data; collect warnings
         -> JSON response (or error)
  React: show previews, scores, chart and warnings
```

## Reference storage

```text
backend/
  references/
    mars-gale/            reference_id = mars-gale
      dem.tif             validated numerical Mars elevation GeoTIFF
      preview.png         prepared Mars terrain visualization
      metadata.json       verified source and geospatial metadata
```

- The backend owns the Mars DEM and the reference metadata. The frontend neither stores nor analyzes the Mars DEM.
- The backend serves `preview.png` to the frontend through the static path in the [API contract](api-contract.md) (`/static/references/mars-gale/preview.png`). Wiring that mount is Phase 1 work.
- Mars terrain features are computed from `dem.tif` and cached by the backend during implementation (Phase 1 or later). None exist yet.
- Source provenance comes from the verified `metadata.json`, not from assumptions.

## Feature cache

Cached Mars features must match the current metric definitions and processing scale. **Proposal:** key each cache entry by reference ID, methodology version and processing scale. Recompute an entry when any part of its key changes. The cache format and location are unresolved.

## Boundaries

- The backend is authoritative for validation, units, numerical processing and scoring.
- The frontend renders backend results and does not duplicate algorithms.
- Each `reference_id` maps to a documented, prepared dataset ([data/README.md](../data/README.md)).
- Earth and Mars rasters are compared through terrain descriptors. They are never overlaid in a shared CRS. Comparability (extent, effective resolution, CRS, vertical units, NoData) is checked, and remaining issues become warnings.
- Uploaded and generated rasters stay out of Git.

## Unresolved

The following are undecided:

- Deployment and hosting.
- Runtime and package versions.
- Feature cache format and location (the reference store itself is `backend/references/`).
- Upload retention and processing limits.
- Synchronous versus job-based execution.
- CORS configuration.

No database, queue or cloud provider is planned.

See [methodology](methodology.md) and [contribution rules](../CONTRIBUTING.md).
