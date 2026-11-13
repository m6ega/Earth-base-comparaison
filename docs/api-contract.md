# API contract

No endpoint is implemented. Implementation starts November 14, 2026.

## Approved decisions

- Endpoint: `POST /analyze`.
- Request fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `file` | File | One Earth DEM GeoTIFF |
| `planet` | String | `mars` or `moon` |
| `reference_id` | String | Identifier of a selected, prepared planetary reference |

- The backend analyzes terrain using relative relief, slope distribution and surface roughness. Terrain morphology is deferred beyond the MVP.
- Earth aridity and lithology are optional enrichment. They do not contribute to the terrain similarity score.
- Missing enrichment data must not block terrain analysis: a request with a valid DEM and reference returns terrain results even when enrichment is unavailable.

## Proposals for both leads to review

Examples are illustrative, not executable fixtures or a stable integration contract.

### Request handling

Use `multipart/form-data`. Validate that `reference_id` exists among prepared references and belongs to the selected `planet`. Do not accept arbitrary server paths or remote download URLs as reference identifiers.

### Success response

HTTP `200` after synchronous processing is a candidate design. If resource estimates require asynchronous jobs, revise this contract jointly before implementation.

Illustrative JSON shape (null values deliberately avoid inventing scores):

```json
{
  "planet": "mars",
  "reference_id": "example-reference",
  "methodology_version": "TBD",
  "similarity": { "score": null, "scale": null },
  "metrics": {
    "relative_relief": { "earth": null, "reference": null, "unit": null },
    "slope_distribution": { "earth": null, "reference": null, "unit": null },
    "surface_roughness": { "earth": null, "reference": null, "unit": null }
  },
  "enrichment": {
    "aridity": { "status": "unavailable", "value": null },
    "lithology": { "status": "unavailable", "value": null }
  },
  "warnings": []
}
```

`enrichment` is reported separately from `similarity` and never changes the score. Its value types, status vocabulary and sources are unresolved. Metric representations may be scalars, distributions or descriptors and must be finalized with the methodology. Nullability, score range, precision, processing metadata and warning schema are unresolved; this example does not promise nulls in production.

### Errors

| Status | Intended use |
| --- | --- |
| `400` | Unknown `reference_id` or inconsistent `planet`/`reference_id` pair |
| `413` | Upload exceeds the agreed limit |
| `415` | Unsupported file format |
| `422` | Missing fields or unusable elevation data |
| `500` | Unexpected processing failure |

Unavailable enrichment is not an error; at most it produces a warning.

Proposed common shape:

```json
{
  "error": {
    "code": "INVALID_DEM",
    "message": "The uploaded raster cannot be analyzed.",
    "details": []
  }
}
```

Agree on whether framework validation errors are normalized into this shape. Avoid exposing internal paths or stack traces. Warnings indicate qualified results; errors indicate that analysis could not be completed.

## Unresolved details

- Upload size, dimensions, band requirements and resource/time limits.
- CRS, elevation units, NoData handling and minimum usable coverage.
- `reference_id` naming, how available references reach the frontend, and versioning.
- Synchronous execution feasibility and timeout behavior.
- Metric value types, score definition, units and visualization needs.
- Enrichment value types, status values and data sources.
- Error/warning schema, CORS/deployment configuration and retention policy.

See [architecture](architecture.md), [methodology](methodology.md), and [data plan](../data/README.md).
