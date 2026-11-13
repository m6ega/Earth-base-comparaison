# Backend preparation

**Status:** documentation only; implementation starts November 14, 2026.

## Approved decisions

[Project context](../PROJECT-CONTEXT.md) assigns the Backend Lead responsibility for the backend, terrain processing, similarity algorithm and API. The planned stack is FastAPI, Rasterio, NumPy and SciPy. Backend work happens on `backend--dev`, with pull requests to `main` approved by humans.

Responsibilities are file validation, DEM preprocessing, resolution harmonization, terrain feature extraction, similarity calculations and API responses. The Backend Lead also validates, prepares, stores and integrates the planetary reference data researched by the Frontend & Data Lead.

`POST /analyze` accepts `file` (one Earth DEM GeoTIFF), `planet` (`mars` or `moon`) and `reference_id`. MVP metrics are relative relief, slope distribution and surface roughness; terrain morphology is deferred.

Responses follow the approved mock files [analyze-success.json](../data/examples/analyze-success.json) and [analyze-error.json](../data/examples/analyze-error.json). A successful response always includes `total_similarity` and the three per-metric `scores`, each from 0 to 1. The 0–1 range is an API convention; the formula, normalization and weights are not approved. Scores describe geometric terrain similarity only, not habitability or base suitability.

Earth aridity and lithology are deferred optional features, not approved for the MVP. Do not implement them without separate approval.

## Proposed implementation sequence

Beginning at the hackathon:

1. Agree on the remaining [API contract](../docs/api-contract.md) details and the [methodology](../docs/methodology.md) with the Frontend & Data Lead.
2. Select supported runtime and package versions and document reproducible setup.
3. Validate and prepare the planetary reference data documented in [data/README.md](../data/README.md).
4. Implement validation and bounded processing of the uploaded Earth DEM and the selected reference.
5. Implement the agreed preprocessing and the three MVP terrain metrics.
6. Return results, warnings and errors in the shape of the approved mock files.
7. Validate with controlled test surfaces and representative datasets.

No modules, dependencies, runtime commands or deployment environment are established yet.

## Open questions

Upload/resource limits, CRS and unit handling, NoData thresholds, processing timeouts, synchronous versus asynchronous processing, score formula and weights, error code list and HTTP status mapping, warning item schema, reference storage location and data retention remain unresolved. Resolve these before the corresponding implementation.

See [architecture](../docs/architecture.md), [data guidance](../data/README.md), and [contribution rules](../CONTRIBUTING.md).
