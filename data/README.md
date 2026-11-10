# Data preparation

## Confirmed scope

Users supply an Earth DEM and select a reference region on Mars or the Moon. There is no global Earth scanning. The Frontend & Data Lead owns data source research and reference datasets, working with the Backend Lead on processing compatibility. See [project context](../PROJECT-CONTEXT.md).

## Proposed reference selection criteria

Choose a small, documented reference set with reliable provenance, clear usage terms, known horizontal and vertical units, appropriate spatial extent, and sufficient valid elevation coverage. Compare effective resolution and terrain scale before treating datasets as comparable. No specific source, region or dataset has been approved yet.

For each selected dataset, record:

- Stable identifier, planet, region name and geographic bounds.
- Provider, source URL, product/version and retrieval date.
- Usage terms, attribution and redistribution conditions.
- Raster format, band, dimensions, pixel spacing and effective resolution.
- Coordinate reference system, planetary body definition, horizontal units, vertical units and datum.
- NoData convention, quality notes, checksum and processing history.
- Download and preparation instructions sufficient to reproduce the reference.

## Proposed storage policy

Keep large source rasters, uploaded files, generated products and archives outside Git. The root `.gitignore` excludes common raster formats and local data directories; it does not enforce a file-size limit or remove previously tracked files. Document approved download locations rather than committing datasets. Git LFS or external object storage requires a later team decision.

Small fixtures may be considered during development after checking licensing and repository size; any ignore-rule exception must be explicit and reviewed. The repository MIT license does not establish rights to third-party data.

## Open questions

Reference regions and providers, file format, minimum coverage, resolution targets, download hosting, retention/deletion policy for uploads and storage budget remain undecided. No datasets have been downloaded or validated as part of repository preparation.

See [methodology](../docs/methodology.md) and [API contract](../docs/api-contract.md).
