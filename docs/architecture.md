# Architecture plan

## Confirmed decisions

[PROJECT-CONTEXT.md](../PROJECT-CONTEXT.md) is authoritative. React handles the interface; FastAPI handles analysis, using Rasterio for DEM processing and NumPy/SciPy for calculations. Users upload an Earth DEM and select a Mars or Moon reference region. Global Earth scanning is excluded.

The Backend Lead owns processing and the API. The Frontend & Data Lead owns the interface and reference data research.

## Planned processing flow

```text
React: planet + reference selection + Earth DEM upload
                         |
                  POST /analyze
                         |
FastAPI: validate upload and selected reference
                         |
Preprocess Earth and planetary DEMs
                         |
Harmonize resolution and extract terrain features
                         |
Calculate similarity and return results/warnings
                         |
React: visualize results and explain errors/warnings
```

This is a conceptual flow, not implemented behavior. Detailed request/response fields are [proposed](api-contract.md).

## Proposed boundaries

- Backend remains authoritative for validation, units and numerical processing.
- Frontend presents user choices and results without duplicating the similarity algorithm.
- Reference metadata links a stable selection identifier to a documented dataset.
- Uploaded and generated rasters remain outside source control.
- Processing records assumptions and warnings so results can be interpreted and reproduced.

Earth and planetary rasters are compared through terrain descriptors; they are not geographically overlaid in a shared Earth CRS. Body-specific coordinate systems and physical units need explicit treatment.

## Unresolved decisions

Deployment, runtime versions, authentication, catalog delivery, storage, retention, processing limits, synchronous versus job-based execution, and concurrency are undecided. No database, queue, cloud provider, additional endpoint or frontend build tool is mandated by this plan.

See [methodology](methodology.md), [data plan](../data/README.md), and [contribution rules](../CONTRIBUTING.md). Development begins November 14, 2026.
