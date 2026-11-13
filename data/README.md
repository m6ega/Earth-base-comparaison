# Data preparation

## Approved decisions

Users supply one Earth DEM GeoTIFF and select a prepared planetary reference on Mars or the Moon, identified by `reference_id`. There is no global Earth scanning. See [project context](../PROJECT-CONTEXT.md).

Responsibilities for planetary reference data:

| Step | Owner role |
| --- | --- |
| Research NASA planetary DEM sources and document provenance | Frontend & Data Lead |
| Validate, prepare, store and integrate the reference for analysis | Backend Lead |

Earth aridity and lithology are optional enrichment. They do not contribute to the terrain similarity score, and missing enrichment data must not block terrain analysis.

No specific source, region, product or dataset has been selected yet. No datasets have been downloaded or validated as part of repository preparation.

## Provenance record (required for each reference)

The Frontend & Data Lead records, for each planetary reference:

- Proposed `reference_id`, planet, region name and geographic bounds.
- Provider, source URL, product/version and retrieval date.
- Usage terms, attribution and redistribution conditions.
- Raster format, band, dimensions, pixel spacing and effective resolution.
- Coordinate reference system, planetary body definition, horizontal units, vertical units and datum.
- NoData convention and known quality notes.
- Download instructions sufficient to reproduce the source.

The Backend Lead adds the validation result, preparation steps, checksum and storage location before the reference is used by `POST /analyze`.

Optional enrichment sources (aridity, lithology) need the same provenance and usage-terms record before use.

## Proposed selection criteria

Choose a small, documented reference set with reliable provenance, clear usage terms, known horizontal and vertical units, appropriate spatial extent, and sufficient valid elevation coverage. Compare effective resolution and terrain scale before treating datasets as comparable.

## Proposed storage policy

Keep large source rasters, uploaded files, generated products and archives outside Git. The root `.gitignore` excludes common raster formats and local data directories; it does not enforce a file-size limit or remove previously tracked files. Document approved download locations rather than committing datasets. Git LFS or external object storage requires a later team decision.

Small fixtures may be considered during development after checking licensing and repository size; any ignore-rule exception must be explicit and reviewed. The repository MIT license does not establish rights to third-party data.

## Open questions

Reference regions and NASA products, `reference_id` naming, minimum coverage, resolution targets, reference storage location, enrichment data sources, retention/deletion policy for uploads and storage budget remain undecided.

See [methodology](../docs/methodology.md) and [API contract](../docs/api-contract.md).
