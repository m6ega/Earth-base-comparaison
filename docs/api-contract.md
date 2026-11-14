# API contract

**Version:** draft 0.2 (Phase 0). **Status:** endpoints and request fields are approved. The response fields for previews, chart data, warnings and reference metadata are a proposal that is **pending review by the Frontend & Data Lead** before final approval.

No endpoint is implemented yet. Scope and decisions: [PROJECT-CONTEXT.md](../PROJECT-CONTEXT.md).

## Approved endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness check |
| `GET` | `/references` | List the prepared Mars references the user can select |
| `POST` | `/analyze` | Compare one uploaded Earth GeoTIFF with one Mars reference |

### `POST /analyze` request

`multipart/form-data`:

| Field | Type | Meaning |
| --- | --- | --- |
| `file` | File | One Earth elevation GeoTIFF |
| `reference_id` | String | `id` of a reference returned by `GET /references` |

The previous `planet` field is removed. The MVP is Mars only.

## Common schema

All JSON examples in [data/examples/](../data/examples/) use exactly this schema.

### Reference object

Used in `GET /references` and in the `POST /analyze` success response.

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | String | Stable reference identifier, used as `reference_id` |
| `name` | String | Display name, for example `Gale Crater` |
| `dataset` | String | Source dataset label. Exact product details live in [data/README.md](../data/README.md) |
| `effective_resolution_m` | Number or `null` | Effective horizontal resolution in metres; `null` until verified |
| `preview_url` | String | Mars terrain preview image (see [Preview images](#preview-images)) |

### Warning object

| Field | Type | Meaning |
| --- | --- | --- |
| `code` | String | Machine-readable code |
| `message` | String | Human-readable explanation for display |

Warnings qualify a completed result, for example limited valid coverage or a resolution difference. Errors mean that no result was produced. The full list of warning codes is unresolved.

### `is_mock` flag

Every `GET /references` and `POST /analyze` success response has a boolean `is_mock`.

- `false`: values were calculated by the backend from real data.
- `true`: values are mock or demo data. Clients must label them visibly as mock data and never present them as scientific results.

All files in `data/examples/` have `is_mock: true`. They are test fixtures only.

## Responses

### `GET /health`

`200`:

```json
{ "status": "ok" }
```

Fixture: [health.json](../data/examples/health.json).

### `GET /references`

`200`:

```json
{
  "is_mock": true,
  "references": [
    {
      "id": "mars-gale",
      "name": "Gale Crater",
      "dataset": "NASA MGS MOLA",
      "effective_resolution_m": null,
      "preview_url": "/static/references/mars-gale/preview.png"
    }
  ]
}
```

Fixture: [references.json](../data/examples/references.json). Gale Crater is the required reference. Gusev Crater appears only after it is prepared. The `mars-gale` identifier is proposed.

### `POST /analyze` success

`200`:

| Field | Type | Meaning |
| --- | --- | --- |
| `status` | String | `success` |
| `is_mock` | Boolean | See [`is_mock` flag](#is_mock-flag) |
| `reference` | Reference object | The selected Mars reference |
| `total_similarity` | Number | Overall geometric similarity, `0`–`1` |
| `scores.relative_relief` | Number | `0`–`1` |
| `scores.slope_distribution` | Number | `0`–`1` |
| `scores.surface_roughness` | Number | `0`–`1` |
| `earth_preview_url` | String | Earth terrain preview image (see [Preview images](#preview-images)) |
| `charts.slope_distribution.unit` | String | Slope unit, `degrees` |
| `charts.slope_distribution.bin_edges` | Number array | `n + 1` bin edges |
| `charts.slope_distribution.earth` | Number array | `n` values: fraction of valid Earth cells per bin, summing to about 1 |
| `charts.slope_distribution.mars` | Number array | `n` values, the same for the Mars reference |
| `warnings` | Warning object array | Always present; empty when there are none |

The Mars preview is `reference.preview_url`. There is no separate Mars preview field.

Fixture: [analyze-success.json](../data/examples/analyze-success.json). All numbers in it, including bin edges, are illustrative.

### Error

Any endpoint may return:

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
| `error.code` | String | Machine-readable code |
| `error.message` | String | Human-readable explanation for display |

Fixture: [analyze-error.json](../data/examples/analyze-error.json).

## Preview images

Clients use both preview URL fields directly as an image source (`<img src>`). They are opaque strings, so clients must not construct or parse them.

Proposal for the backend implementation:

- **Mars preview** (`reference.preview_url`): a PNG generated once per reference during reference preparation. It is served by FastAPI as a static file under `/static/references/{id}/preview.png`, a path relative to the API base URL. This is a static file mount, not an additional API endpoint.
- **Earth preview** (`earth_preview_url`): a PNG rendered from the uploaded DEM during `POST /analyze` and returned inline as a `data:image/png;base64,...` URL. The upload then need not be stored after the request, and no further endpoint is needed.

Preview size, colour map and hillshading are unresolved.

## Score convention

- `total_similarity` and all three `scores` are mandatory in every success response.
- `0`–`1` is an API convention: `1.0` is maximum and `0.0` minimum geometric terrain similarity. It is not a validated scientific calculation, and the formula, normalization and weights are not approved (see [methodology](methodology.md)).
- Scores are not probabilities and do not indicate habitability or base suitability.

## Proposals for review

### Request handling

Reject a `reference_id` that is not in the prepared reference list. Never accept server paths or remote URLs as references. HTTP `200` after synchronous processing is the candidate design. If processing cost requires asynchronous jobs, revise this contract jointly first.

### HTTP status codes for errors

| Status | Intended use |
| --- | --- |
| `400` | Unknown `reference_id` |
| `413` | Upload exceeds the agreed limit |
| `415` | Unsupported file format |
| `422` | Missing fields or unusable elevation data, for example `INVALID_DEM` |
| `500` | Unexpected processing failure |

Decide whether FastAPI validation errors are normalized into the error shape. Never expose internal paths or stack traces.

## Unresolved details

- Upload size, dimensions, band requirements and time limits.
- CRS, vertical units, NoData handling and minimum valid coverage.
- Final `reference_id` naming and versioning.
- Slope bin edges, preview rendering and numeric precision.
- Full lists of error and warning codes and their HTTP statuses.
- Whether responses carry a methodology or reference-data version.
- CORS, deployment and upload retention.

See [architecture](architecture.md), [methodology](methodology.md) and the [data plan](../data/README.md).
