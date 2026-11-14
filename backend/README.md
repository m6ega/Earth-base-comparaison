# Backend

**Status:** no code yet. Implementation starts in Phase 1.

**Owner:** Backend Lead + Claude, on `backend--dev`. Scope, stack and responsibilities: [PROJECT-CONTEXT.md](../PROJECT-CONTEXT.md).

The backend implements the three MVP endpoints in the [API contract](../docs/api-contract.md). It stores and processes the Mars MOLA references, caches precomputed Mars features, and returns responses in the shape of the fixtures in [data/examples/](../data/examples/). Real responses always have `is_mock: false`.

## Mars reference storage

The backend owns the Mars DEM and reference metadata:

```text
backend/references/mars-gale/
  dem.tif         validated numerical Mars elevation GeoTIFF
  preview.png     prepared Mars terrain visualization
  metadata.json   verified source and geospatial metadata
```

Reference ID: `mars-gale`. The backend serves `preview.png` to the frontend, which does not store or analyze the Mars DEM. Mars terrain features are computed from `dem.tif` and cached by the backend in the implementation phase. Source provenance comes from `metadata.json`. Git tracking policy: [data/README.md](../data/README.md#storage).

## Proposed implementation sequence

1. Select Python and package versions (FastAPI, Rasterio, NumPy; SciPy only if needed). Document reproducible setup.
2. `GET /health`.
3. Load the prepared Gale Crater reference from `backend/references/mars-gale/`, re-validate it against `metadata.json`, serve its preview and cache its features.
4. `GET /references`.
5. `POST /analyze`: upload validation, comparability checks, the three metrics, scores, Earth preview, slope chart data and warnings ([methodology](../docs/methodology.md)).
6. Tests with synthetic surfaces and representative DEMs.
7. Optional: add Gusev Crater after the first working comparison.

## Open questions

See the unresolved lists in the [API contract](../docs/api-contract.md#unresolved-details) and [architecture](../docs/architecture.md#unresolved).
