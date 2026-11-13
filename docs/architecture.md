# Architecture plan

## Approved decisions

[PROJECT-CONTEXT.md](../PROJECT-CONTEXT.md) is authoritative. React handles the interface; FastAPI handles analysis, using Rasterio for DEM processing and NumPy/SciPy for calculations. Users upload one Earth DEM GeoTIFF and select a planet (`mars` or `moon`) and a prepared planetary reference (`reference_id`). Global Earth scanning is excluded.

The Backend Lead owns processing, the API, and the validation, preparation, storage and integration of planetary reference data. The Frontend & Data Lead owns the interface, research of NASA reference data, and provenance documentation.

Terrain similarity uses relative relief, slope distribution and surface roughness. Terrain morphology is deferred beyond the MVP. Earth aridity and lithology are optional enrichment, kept outside the similarity calculation; their absence must not block terrain analysis.

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
Calculate terrain similarity
                         |
Optional: attach Earth aridity/lithology if available
(not used in the score; never blocks the response)
                         |
Return results, enrichment and warnings
                         |
React: visualize results and explain errors/warnings
```

This is a conceptual flow, not implemented behavior. Detailed response fields are [proposed](api-contract.md).

## Proposed boundaries

- Backend remains authoritative for validation, units and numerical processing.
- Frontend presents user choices and results without duplicating the similarity algorithm.
- Reference metadata links each `reference_id` to a documented, prepared dataset.
- Uploaded and generated rasters remain outside source control.
- Processing records assumptions and warnings so results can be interpreted and reproduced.

Earth and planetary rasters are compared through terrain descriptors; they are not geographically overlaid in a shared Earth CRS. Body-specific coordinate systems and physical units need explicit treatment.

## Unresolved decisions

Deployment, runtime versions, authentication, how available references reach the frontend, reference storage, retention, processing limits, synchronous versus job-based execution, enrichment data sources and concurrency are undecided. No database, queue, cloud provider, additional endpoint or frontend build tool is mandated by this plan.

See [methodology](methodology.md), [data plan](../data/README.md), and [contribution rules](../CONTRIBUTING.md). Development begins November 14, 2026.
