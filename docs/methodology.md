# Terrain comparison methodology — draft

## Approved decisions

[Project context](../PROJECT-CONTEXT.md) specifies comparison of one uploaded Earth DEM GeoTIFF with a selected, prepared Mars or Moon reference (`reference_id`).

- MVP terrain similarity metrics: relative relief, slope distribution and surface roughness.
- Terrain morphology (for example, TPI) is deferred beyond the MVP. It remains documented below as a future extension.
- Earth aridity and lithology are optional enrichment. They do not contribute to the terrain similarity score, and missing enrichment data must not block terrain analysis.
- Preprocessing and resolution harmonization are backend responsibilities. The Backend Lead validates and prepares the planetary reference; the Frontend & Data Lead documents its provenance.

No formulas, thresholds or weighting scheme are approved.

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

## Optional enrichment: aridity and lithology

Earth aridity and lithology may be reported as context for the uploaded Earth location.

- They are reported separately from terrain results and are not inputs to the similarity score.
- If enrichment data is unavailable, terrain analysis still completes; the result notes that enrichment is unavailable.
- Data sources, resolution, classification schemes and how values are presented are unresolved. Each source needs provenance and usage terms recorded in [data/README.md](../data/README.md).

## Proposed comparison and scoring

Start with transparent per-metric comparisons of the three MVP metrics. Agree on normalization and distance functions before combining metrics with different units. An aggregate score is optional pending agreement on weights, missing-metric behavior and calibration. Do not choose or imply a 0–100 scale until its meaning is established.

Record dataset versions, preprocessing choices, analysis scale and methodology version with results. Warn when resolution or coverage limits comparability. Terrain similarity is not a probability, proof of a physical analog, or evidence of comparable atmosphere, geology, gravity or mission suitability.

## Validation plan for development

- Use flat, tilted and synthetic rough surfaces with known qualitative behavior.
- Check identical-input comparisons where the selected metric is mathematically defined.
- Check invariance to constant elevation offsets where the descriptor should be invariant.
- Test unit conversion, NoData masks, edge effects and sensitivity to resolution/window size.
- Check that terrain results are unchanged whether enrichment data is present or absent.
- Compare representative real datasets and document limitations rather than claiming unmeasured accuracy.

All validation is planned for application development beginning November 14, 2026. Dataset choices, metric formulas, minimum coverage, resampling, weights and acceptance thresholds remain open.

See [data requirements](../data/README.md) and [API contract](api-contract.md).
