# Terrain comparison methodology — draft

## Confirmed scope

[Project context](../PROJECT-CONTEXT.md) specifies comparison of an uploaded Earth DEM with a selected Mars or Moon reference region, using relative relief, slope distribution, surface roughness and terrain morphology. Preprocessing and resolution harmonization are backend responsibilities. No formulas, thresholds or weighting scheme are confirmed.

**The methods below are proposals requiring team review and validation.** No algorithm has been implemented or benchmarked.

## Proposed preprocessing

1. Inspect format, elevation band, bounds, CRS, physical units and valid-data coverage.
2. Identify NoData and non-finite values; reject inadequate coverage using an agreed threshold. Do not treat missing elevations as zero.
3. Convert horizontal and vertical measurements into documented compatible units. Handle each planetary body's coordinate definition explicitly.
4. Agree on comparable physical extent, effective resolution and analysis scale. Resampling to finer pixels does not create new terrain information.
5. Resample using an agreed method, preserving masks and recording any edge treatment.
6. Extract the same descriptors under the same conventions for both datasets.

Do not geographically co-register an Earth region with a planetary region. Compare descriptors of their terrain. Avoid raw derivatives in angular coordinates without an appropriate physical-distance treatment.

## Candidate metric definitions

| Confirmed metric | Proposed operational definition | Unresolved choices |
| --- | --- | --- |
| Relative relief | Elevation range over a defined area; consider a robust percentile range | Extent/window, percentile cutoffs, units and outlier treatment |
| Slope distribution | Distribution of local slope angles computed from physical elevation gradients | Derivative method, histogram bins, edges and distribution distance |
| Surface roughness | Dispersion of elevation residuals after removing a local trend | Detrending method, neighborhood scale and normalization |
| Terrain morphology | Descriptors of terrain shape, potentially based on curvature or landform classes | Descriptor family, scale, class definitions and comparison distance |

These are candidates, not a commitment to particular equations. Morphology is especially underspecified and needs an explicit, feasible definition before implementation.

## Proposed comparison and scoring

Start with transparent per-metric comparisons. Agree on normalization and distance functions before combining metrics with different units. An aggregate score is optional pending agreement on weights, missing-metric behavior and calibration. Do not choose or imply a 0–100 scale until its meaning is established.

Record dataset versions, preprocessing choices, analysis scale and methodology version with results. Warn when resolution or coverage limits comparability. Terrain similarity is not a probability, proof of a physical analog, or evidence of comparable atmosphere, geology, gravity or mission suitability.

## Validation plan for development

- Use flat, tilted and synthetic rough surfaces with known qualitative behavior.
- Check identical-input comparisons where the selected metric is mathematically defined.
- Check invariance to constant elevation offsets where the descriptor should be invariant.
- Test unit conversion, NoData masks, edge effects and sensitivity to resolution/window size.
- Compare representative real datasets and document limitations rather than claiming unmeasured accuracy.

All validation is planned for application development beginning November 14, 2026. Dataset choices, metric formulas, minimum coverage, resampling, weights and acceptance thresholds remain open.

See [data requirements](../data/README.md) and [draft API contract](api-contract.md).
