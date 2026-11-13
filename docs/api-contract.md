# API contract

No endpoint is implemented. Implementation starts November 14, 2026.

## Approved decisions

### Endpoint and request

- Endpoint: `POST /analyze`.
- Request fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `file` | File | One Earth DEM GeoTIFF |
| `planet` | String | `mars` or `moon` |
| `reference_id` | String | Identifier of a selected, prepared planetary reference |

- The backend analyzes terrain using relative relief, slope distribution and surface roughness. Terrain morphology is deferred beyond the MVP.

### MVP mock responses

The mock response files below define the MVP response shape for frontend and backend integration:

- Success: [data/examples/analyze-success.json](../data/examples/analyze-success.json)
- Error: [data/examples/analyze-error.json](../data/examples/analyze-error.json)

Success response:

```json
{
  "status": "success",
  "planet": "mars",
  "reference": {
    "id": "mars-demo-01",
    "name": "Mars Demo Reference"
  },
  "total_similarity": 0.78,
  "scores": {
    "relative_relief": 0.82,
    "slope_distribution": 0.75,
    "surface_roughness": 0.77
  },
  "warnings": []
}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `status` | String | `success` |
| `planet` | String | Echo of the requested `planet` |
| `reference.id` | String | Echo of the requested `reference_id` |
| `reference.name` | String | Display name of the prepared reference |
| `total_similarity` | Number | Overall terrain similarity, `0`–`1` |
| `scores.relative_relief` | Number | Per-metric similarity, `0`–`1` |
| `scores.slope_distribution` | Number | Per-metric similarity, `0`–`1` |
| `scores.surface_roughness` | Number | Per-metric similarity, `0`–`1` |
| `warnings` | Array | Conditions that qualify the result; always present, empty when none. The schema of a non-empty warning entry is unresolved |

Error response:

```json
{
  "status": "error",
  "error": {
    "code": "INVALID_DEM",
    "message": "The uploaded file is not a valid DEM GeoTIFF."
  }
}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `status` | String | `error` |
| `error.code` | String | Machine-readable error code |
| `error.message` | String | Human-readable explanation for display |

### Score convention

- `total_similarity` and all three `scores` are mandatory in every successful MVP response.
- The `0`–`1` range for `total_similarity` and `scores` is an MVP API convention for display and integration, not an approved scientific formula.
- `1.0` represents maximum terrain similarity and `0.0` minimum terrain similarity. This is an MVP interface convention, not a scientifically validated calculation.
- Scores measure geometric terrain similarity only. They do not indicate habitability or base suitability.
- All numeric values in the mock files are illustrative. They are not results from any dataset and must not be presented as scientific findings.
- How per-metric scores are calculated and how they combine into `total_similarity` (weights, normalization, distance functions) is not approved. See [methodology](methodology.md).
- A score is not a probability and does not establish physical analogy or mission suitability.

### Deferred optional features

Earth aridity and lithology are **not approved for the MVP**. They are deferred optional features that require separate approval before being added to the API. The MVP responses contain no enrichment fields. If they are approved later, they must not contribute to the terrain similarity score, and missing data for them must not block terrain analysis.

## Proposals for both leads to review

### Request handling

Use `multipart/form-data`. Validate that `reference_id` exists among prepared references and belongs to the selected `planet`. Do not accept arbitrary server paths or remote download URLs as reference identifiers.

HTTP `200` after synchronous processing is a candidate design. If resource estimates require asynchronous jobs, revise this contract jointly before implementation.

### HTTP status codes for errors

| Status | Intended use |
| --- | --- |
| `400` | Unknown `reference_id` or inconsistent `planet`/`reference_id` pair |
| `413` | Upload exceeds the agreed limit |
| `415` | Unsupported file format |
| `422` | Missing fields or unusable elevation data, for example `INVALID_DEM` |
| `500` | Unexpected processing failure |

Agree on whether framework validation errors are normalized into the error response shape. Avoid exposing internal paths or stack traces. Warnings indicate qualified results; errors indicate that analysis could not be completed.

## Unresolved details

- Upload size, dimensions, band requirements and resource/time limits.
- CRS, elevation units, NoData handling and minimum usable coverage.
- `reference_id` naming, how available references reach the frontend, and versioning.
- Synchronous execution feasibility and timeout behavior.
- Score calculation, weights, numeric precision and visualization needs.
- Full list of error codes and the HTTP status for each.
- Schema of non-empty `warnings` entries (`warnings` stays an array; the mock shows only an empty one).
- CORS/deployment configuration and retention policy.

See [architecture](architecture.md), [methodology](methodology.md), and [data plan](../data/README.md).
