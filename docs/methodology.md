# Terrain comparison methodology — draft

## Approved decisions

[Project context](../PROJECT-CONTEXT.md) specifies comparison of one uploaded Earth DEM GeoTIFF with a selected, prepared Mars or Moon reference (`reference_id`).

- MVP terrain similarity metrics: relative relief, slope distribution and surface roughness.
- Terrain morphology (for example, TPI) is deferred beyond the MVP. It remains documented below as a future extension.
- A successful analysis always returns `total_similarity` and one score per MVP metric, each a number from 0 to 1 (see [API contract](api-contract.md#score-convention)). The 0–1 range is an API convention, not an approved scientific formula.
- Scores measure geometric terrain similarity only. They do not indicate habitability or base suitability.
- Earth aridity and lithology are deferred optional features, not approved for the MVP. They require separate human approval.
- Preprocessing and resolution harmonization are backend responsibilities. The Backend Lead validates and prepares the planetary reference; the Frontend & Data Lead documents its provenance.

No formulas, normalization, thresholds or weighting scheme are approved.

**The methods below are proposals requiring team review and validation.** No algorithm has been implemented or benchmarked.

## Proposed preprocessing

1. Inspect format, elevation band, bounds, CRS, physical units and valid-data coverage.
2. Identify NoData and non-finite values; reject inadequate coverage using an agreed threshold. Do not treat missing elevations as zero.
3. Convert horizontal and vertical measurements into documented compatible units. Handle each planetary body's coordinate definition explicitly.
4. Agree on comparable physical extent, effective resolution and analysis scale. Resampling to finer pixels does not create new terrain information.
5. Resample using an agreed method, preserving masks and recording any edge treatment.
6. Extract the same descriptors under the same conventions for both datasets.

Do not geographically co-register an Earth region with a planetary region. Compare descriptors of their terrain. Avoid raw derivatives in angular coordinates without an appropriate physical-distance treatment.

## Candidate MVP metric definitions

| Approved MVP metric | Proposed operational definition | Unresolved choices |
| --- | --- | --- |
| Relative relief | Elevation range over a defined area; consider a robust percentile range | Extent/window, percentile cutoffs, units and outlier treatment |
| Slope distribution | Distribution of local slope angles computed from physical elevation gradients | Derivative method, histogram bins, edges and distribution distance |
| Surface roughness | Dispersion of elevation residuals after removing a local trend | Detrending method, neighborhood scale and normalization |

These are candidates, not a commitment to particular equations.

## Future extension: terrain morphology

Terrain morphology was part of the initial metric list and is deferred beyond the MVP. A candidate approach is a topographic position index (TPI) or other descriptors of terrain shape, such as curvature or landform classes. Descriptor family, scale, class definitions and comparison distance are unresolved, and an explicit, feasible definition is needed before it is added.

## Deferred optional features: aridity and lithology

Earth aridity and lithology were discussed as possible context for the uploaded Earth location. They are not approved for the MVP. Their datasets, algorithms, response schema and presentation are not approved, and they are not part of terrain similarity. Adding them requires separate human approval.

## Proposed comparison and scoring

The API requires each of the three MVP metric scores and `total_similarity` to be a number from 0 to 1. How to reach that range is not decided:

- Proposal: compare each metric transparently between the Earth DEM and the reference, then map the difference to a 0–1 per-metric score.
- Proposal: derive `total_similarity` from the three per-metric scores.
- Unresolved: distance functions, normalization, weights, behavior when a metric cannot be computed, and calibration.

Approved MVP interface convention: `1.0` represents maximum terrain similarity and `0.0` minimum terrain similarity. This fixes the direction of the scale for the API and interface only; it is not a scientifically validated calculation. The values in the mock files are illustrative.

Record dataset versions, preprocessing choices, analysis scale and methodology version with results. Warn when resolution or coverage limits comparability. Terrain similarity is geometric only. It is not a probability, proof of a physical analog, or evidence of habitability, base suitability, comparable atmosphere, geology or gravity.
## Validation plan for development

- Use flat, tilted and synthetic rough surfaces with known qualitative behavior.
- Check identical-input comparisons where the selected metric is mathematically defined.
- Check invariance to constant elevation offsets where the descriptor should be invariant.
- Test unit conversion, NoData masks, edge effects and sensitivity to resolution/window size.
- Check that every score stays within 0–1 and that identical inputs score at or near `1.0` under the chosen method.
- Compare representative real datasets and document limitations rather than claiming unmeasured accuracy.

All validation is planned for application development beginning November 14, 2026. Dataset choices, metric formulas, minimum coverage, resampling, weights and acceptance thresholds remain open.

See [data requirements](../data/README.md) and [API contract](api-contract.md).
