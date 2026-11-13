# Architecture plan

## Approved decisions

[PROJECT-CONTEXT.md](../PROJECT-CONTEXT.md) is authoritative. React handles the interface; FastAPI handles analysis, using Rasterio for DEM processing and NumPy/SciPy for calculations. Users upload one Earth DEM GeoTIFF and select a planet (`mars` or `moon`) and a prepared planetary reference (`reference_id`). Global Earth scanning is excluded.

The Backend Lead owns processing, the API, and the validation, preparation, storage and integration of planetary reference data. The Frontend & Data Lead owns the interface, research of NASA reference data, and provenance documentation.

Terrain similarity uses relative relief, slope distribution and surface roughness. A successful response always includes `total_similarity` and per-metric `scores` (0–1 API convention; formula not approved) plus `warnings`, matching the [approved mock responses](api-contract.md#mvp-mock-responses). Scores describe geometric terrain similarity only, not habitability or base suitability. Terrain morphology is deferred beyond the MVP. Earth aridity and lithology are deferred optional features, not approved for the MVP, and have no place in the MVP flow.

Backend work happens on `backend--dev`, frontend work on `frontend--dev`, and reviewed integration on `main` through human-approved pull requests.

## Planned processing flow

```text
React: planet + reference_id selection + Earth DEM GeoTIFF upload
                         |
                  POST /analyze
                         |
FastAPI: validate file, planet and reference_id
                         |
Load prepared planetary reference
                         |
Preprocess Earth DEM; harmonize resolution
                         |
Extract MVP terrain features (relief, slope, roughness)
                         |
Calculate per-metric scores and total_similarity (0-1)
                         |
Return status, planet, reference, scores and warnings
(or status "error" with error code and message)
                         |
React: visualize results and explain errors/warnings
```

This is a conceptual flow, not implemented behavior. Response fields are defined in the [API contract](api-contract.md).

## Proposed boundaries

- Backend remains authoritative for validation, units and numerical processing.
- Frontend presents user choices and results without duplicating the similarity algorithm.
- Reference metadata links each `reference_id` to a documented, prepared dataset.
- Uploaded and generated rasters remain outside source control.
- Processing records assumptions and warnings so results can be interpreted and reproduced.

Earth and planetary rasters are compared through terrain descriptors; they are not geographically overlaid in a shared Earth CRS. Body-specific coordinate systems and physical units need explicit treatment.

## Unresolved decisions

Deployment, runtime versions, authentication, how available references reach the frontend, reference storage, retention, processing limits, synchronous versus job-based execution and concurrency are undecided. No database, queue, cloud provider, additional endpoint or frontend build tool is mandated by this plan.

See [methodology](methodology.md), [data plan](../data/README.md), and [contribution rules](../CONTRIBUTING.md). Development begins November 14, 2026.
