# Data

Scope and data ownership: [PROJECT-CONTEXT.md](../PROJECT-CONTEXT.md#data-ownership).

## Mars references

| Reference | Status | Source |
| --- | --- | --- |
| Gale Crater (`mars-gale`) | Required. Prepared. | NASA MGS MOLA MEGDR (MEG128), source file `megt00n090hb.img`. Verified values: [backend/references/mars-gale/metadata.json](../backend/references/mars-gale/metadata.json). |
| Gusev Crater | Optional, after the first working comparison | NASA MOLA. The exact product is not yet selected or verified. |

The Gale Crater reference was validated: the GeoTIFF reads, and its size (216 x 216 int16 pixels), elevation range and NoData count match `metadata.json`. Gusev Crater has not been downloaded or validated. Do not fill in provenance fields from memory; record only verified values from `metadata.json`. Usage terms, attribution and retrieval date are not yet recorded in `metadata.json` and remain open.

| Step | Owner |
| --- | --- |
| Research the MOLA source and record provenance | Frontend & Data Lead + Codex |
| Validate, prepare, store and cache the reference on the backend | Backend Lead + Claude |

## Provenance record (required for each reference)

Recorded by the Frontend & Data Lead:

- Proposed `reference_id`, region name and bounds.
- Provider, source URL, product name and version, and retrieval date.
- Usage terms, attribution and redistribution conditions.
- Raster format, band, dimensions, pixel spacing and effective resolution.
- CRS, Mars body definition, horizontal units, vertical units and datum.
- NoData convention and quality notes.
- Download steps sufficient to reproduce the source.

Added by the Backend Lead before the reference is served: validation result, preparation steps, checksum, storage location and the processing scale used for cached features.

## Storage

- Mars references live on the backend under `backend/references/<reference_id>/`:

  ```text
  backend/references/mars-gale/
    dem.tif         validated Mars elevation GeoTIFF (72 KB)
    preview.png     prepared Mars terrain visualization
    metadata.json   verified source and geospatial metadata
  ```

- Git policy: `dem.tif` is tracked only because it is 5 MB or smaller, through one narrowly scoped `.gitignore` exception for `backend/references/mars-gale/dem.tif`. Any reference TIFF larger than 5 MB stays local and untracked. The backend developer then obtains the same validated file from the Backend Lead and places it at `backend/references/<reference_id>/dem.tif`.
- Raw NASA source files (such as `megt00n090hb.img`), virtual environments, `node_modules`, secrets and temporary processing data are never committed.
- Cached Mars features are computed by the backend in a later phase and are not tracked. Their location is unresolved.
- Uploaded Earth DEMs are not committed. Their retention is unresolved.
- The root `.gitignore` excludes common raster formats and local data directories. It does not enforce size limits.
- Small test fixtures need a license check and an explicit, reviewed ignore exception.
- The repository's MIT license does not grant rights to third-party data.

## Examples

[examples/](examples/) holds **mock test fixtures** for the [API contract](../docs/api-contract.md): `health.json`, `references.json`, `analyze-success.json` and `analyze-error.json`. Every fixture with results has `is_mock: true`. Their values are illustrative and not derived from any dataset.
