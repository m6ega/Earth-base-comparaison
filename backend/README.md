# Backend preparation

**Status:** documentation only; implementation starts November 14, 2026.

## Confirmed decisions

[Project context](../PROJECT-CONTEXT.md) assigns the Backend Lead responsibility for the backend, terrain processing, similarity algorithm and API. The planned stack is FastAPI, Rasterio, NumPy and SciPy.

Responsibilities are file validation, DEM preprocessing, resolution harmonization, terrain feature extraction, similarity calculations and API responses. The confirmed endpoint is `POST /analyze`.

## Proposed implementation sequence

Beginning at the hackathon:

1. Agree on the [API contract](../docs/api-contract.md) and [methodology](../docs/methodology.md) with the Frontend & Data Lead.
2. Select supported runtime and package versions and document reproducible setup.
3. Implement validation and bounded processing of an Earth DEM and selected reference dataset.
4. Implement the agreed preprocessing and four terrain metrics.
5. Return interpretable results, warnings and structured errors.
6. Validate with controlled test surfaces and representative datasets.

No modules, dependencies, runtime commands or deployment environment are established yet.

## Open questions

Input format, upload/resource limits, CRS and unit handling, NoData thresholds, processing timeouts, synchronous versus asynchronous processing, output schema and data retention remain unresolved. Resolve these before the corresponding implementation.

See [architecture](../docs/architecture.md), [data guidance](../data/README.md), and [contribution rules](../CONTRIBUTING.md).
