# Backend handover — frontend API requirements

The frontend concept is ready for review. Please confirm the API contract before frontend implementation.

## Required endpoints
- `GET /health`
- `GET /references`
- `POST /analyze`

## Frontend needs from `GET /references`
Each reference should expose:
- stable `id`
- display `name`
- `planet`
- centre latitude/longitude and coordinate convention
- dataset/product identifier
- native resolution and units
- availability status

## Frontend needs from `POST /analyze`
- analysis ID and status
- reference metadata
- Earth preview URL and metadata
- Mars preview URL and metadata
- overall similarity and score scale
- relative relief score and comparable source values
- slope distribution score and chart series/bins
- surface roughness score, method and window scale
- short interpretation
- warnings and limitations
- provenance/source identifiers

## Decisions needed
1. Synchronous response or asynchronous job + polling?
2. Upload size limit?
3. Accepted Earth GeoTIFF CRS and elevation units?
4. Exact score formulas and weighting?
5. Definition of relative relief?
6. Slope units and chart format?
7. Roughness algorithm and neighborhood size?
8. Preview URL format/lifetime?
9. Scale bar/extent metadata format?
10. Standard error response schema?

The sample JSON in `docs/ui-concept.md` is a proposal only. Please review and agree field names/types before either side implements against it.
