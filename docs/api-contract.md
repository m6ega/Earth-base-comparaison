# API contract — draft

## Confirmed

[Project context](../PROJECT-CONTEXT.md) confirms `POST /analyze`, an uploaded Earth DEM, a selected planetary reference region, terrain similarity calculation, and API responses. It does not specify serialization, field names, limits or error codes. No endpoint is implemented.

**Everything below is a proposal for both leads to review before implementation.** Examples are illustrative, not executable fixtures or a stable integration contract.

## Proposed request

Use `multipart/form-data` with these fields:

| Field | Proposed type | Meaning |
| --- | --- | --- |
| `earth_dem` | File | Uploaded Earth elevation raster; accepted formats and maximum size TBD |
| `planet` | String | `mars` or `moon` |
| `reference_region_id` | String | Stable identifier from an approved reference catalog |

Validate that the reference exists and belongs to the selected planet. A single-band GeoTIFF is a candidate input format, not a confirmed requirement. Do not accept arbitrary server paths or remote download URLs as reference identifiers.

## Proposed success response

HTTP `200` after synchronous processing is a candidate design. If resource estimates require asynchronous jobs, revise this contract jointly before implementation.

Illustrative JSON shape (null values deliberately avoid inventing scores):

```json
{
  "planet": "mars",
  "reference_region_id": "example-region",
  "methodology_version": "TBD",
  "similarity": { "score": null, "scale": null },
  "metrics": {
    "relative_relief": { "earth": null, "reference": null, "unit": null },
    "slope_distribution": { "earth": null, "reference": null, "unit": null },
    "surface_roughness": { "earth": null, "reference": null, "unit": null },
    "terrain_morphology": { "earth": null, "reference": null, "unit": null }
  },
  "warnings": []
}
```

Metric representations may be scalars, distributions or descriptors and must be finalized with the methodology. Nullability, score range, precision, processing metadata and warning schema are unresolved; this example does not promise nulls in production.

## Proposed errors

| Status | Intended use |
| --- | --- |
| `400` | Invalid selection or inconsistent planet/reference pair |
| `413` | Upload exceeds the agreed limit |
| `415` | Unsupported file format |
| `422` | Missing fields or unusable elevation data |
| `500` | Unexpected processing failure |

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

## Decisions required before integration

- Accepted formats, bands, upload size, dimensions and resource/time limits.
- CRS, elevation units, NoData handling and minimum usable coverage.
- Reference catalog identifiers, metadata delivery and versioning.
- Synchronous execution feasibility and timeout behavior.
- Metric value types, score definition, units and visualization needs.
- Error/warning schema, CORS/deployment configuration and retention policy.

See [architecture](architecture.md), [methodology](methodology.md), and [data plan](../data/README.md).
