# Terrain comparison methodology — draft

Approved metrics, score convention and scientific meaning: [PROJECT-CONTEXT.md](../PROJECT-CONTEXT.md#metrics). Response fields: [API contract](api-contract.md).

No formulas, normalization, thresholds or weights are approved. **Everything below is a proposal requiring team review.** No algorithm has been implemented or benchmarked.

## Comparability checks (required before scoring)

Earth and Mars data must not be treated as directly comparable until the backend has checked the items below. Each unresolved issue becomes a warning in the response.

1. **Physical extent:** compare the areas covered in metres, not pixels or degrees.
2. **Effective resolution:** compare the true information content. Resampling to finer pixels does not create terrain detail.
3. **Coordinate systems:** handle the Earth CRS and the Mars body definition explicitly. Do not take raw derivatives in angular coordinates without converting to physical distance.
4. **Vertical units:** confirm elevation units and datum for both datasets.
5. **NoData handling:** mask NoData and non-finite values. Never treat them as zero. Reject inputs below an agreed valid-coverage threshold.

## Proposed preprocessing

1. Inspect format, elevation band, bounds, CRS, units and valid coverage.
2. Apply the comparability checks above.
3. Bring both datasets to an agreed processing scale with an agreed resampling method, preserving masks.
4. Extract the same descriptors under the same conventions for both datasets.

Do not geographically co-register Earth and Mars regions. Compare descriptors only.

## Candidate metric definitions

| MVP metric | Proposed operational definition | Unresolved choices |
| --- | --- | --- |
| Relative relief | Elevation range over a defined area, possibly a robust percentile range | Window/extent, percentiles, outlier treatment |
| Slope distribution | Distribution of local slope angles from physical elevation gradients | Derivative method, bin edges, distribution distance |
| Surface roughness | Dispersion of elevation residuals after removing a local trend | Detrending method, neighborhood scale, normalization |

The slope histogram behind the slope score is also returned as chart data (see the [API contract](api-contract.md#post-analyze-success)).

## Proposed scoring

- Map each metric's Earth–Mars difference to a 0–1 per-metric score (`1.0` = most similar).
- Derive `total_similarity` from the three per-metric scores.
- Unresolved: distance functions, normalization, weights, behavior when a metric cannot be computed, and calibration.

Record the reference data version, processing scale and methodology version with the results. Changing a metric definition or the processing scale invalidates cached Mars features (see [architecture](architecture.md#feature-cache)).

## Deferred

- **Terrain morphology** (for example, TPI, curvature or landform classes) is deferred beyond the MVP. It needs an explicit, feasible definition first.
- **Earth aridity and lithology** are deferred optional features that require separate approval. They are not part of terrain similarity.

## Validation plan (for implementation)

- Synthetic flat, tilted and rough surfaces with known qualitative behavior.
- Identical inputs score at or near `1.0`, and every score stays within 0–1.
- Invariance to constant elevation offsets where expected.
- Unit conversion, NoData masks, edge effects, and sensitivity to resolution and window size.
- Representative real Earth DEMs against the Gale Crater reference, with limitations documented rather than accuracy claimed.

See the [data plan](../data/README.md).
