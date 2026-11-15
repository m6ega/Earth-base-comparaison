# Methodology 0.4-proposal: artefact-free resampling of rotated and near-native grids

Version 0.4 changes **one processing step only**: how a DEM is resampled onto the
common comparison grid when exact pixel-for-pixel sampling is impossible. Terrain
descriptors (relief, Horn slope, roughness), bins, soft histogram scoring,
Jensen–Shannon distance, equal weights, unit handling, scale/offset decoding,
NoData policy, footprint selection and planetary geometry are unchanged from 0.3
([SCIENTIFIC-FIXES-0.3.md](SCIENTIFIC-FIXES-0.3.md)).

## Defect found in 0.3

The independent scientific review of commit `366312e` found that both lunar
references had their 3 × 3 roughness **inflated** during harmonization.

- Their polar stereographic grids are rotated relative to the local
  azimuthal-equidistant east/north frame (≈130° at Shackleton, ≈31° at Mons
  Mouton), so pixel-aligned sampling never applies.
- 0.3 then used GDAL `average` at a ratio near 1:1. On a rotated grid, GDAL's
  average mixes a varying number of source pixels per cell (often a single
  duplicated or skipped pixel), which creates a staircase pattern: mean roughness
  went from 1.30 m (native pixels) to 4.65 m at Shackleton and from 1.10 m to
  1.68 m at Mons Mouton, with the Laplacian standard deviation (a cell-to-cell
  artefact fingerprint) rising 6.4 → 29.6 m and 5.0 → 9.0 m.
- A ratio sweep showed that on the rotated lunar grids GDAL `average` stays erratic
  and far from an anti-aliased ideal even at 2–3× downsampling, so the defect was
  caused by **rotation**, not only by the near-native ratio. On aligned grids
  (Earth geographic/UTM, Mars equirectangular) GDAL averaging behaved correctly.

Roughness is one third of the total score, so every lunar analysis in 0.3 compared
the Earth DEM against an artificially rough reference. Mars references were not
affected.

## Change in 0.4

For each DEM that is not sampled pixel-aligned:

| Condition | Method |
|---|---|
| Common cell ≥ `AREA_AVERAGE_MIN_RATIO` (2) × the finer source spacing **and** source grid within `AREA_AVERAGE_MAX_ROTATION_DEG` (5°) of the local frame | GDAL area average (unchanged from 0.3) |
| Otherwise (near-native ratios, or rotated grids) | **Interpolated area mean**: a normalized box filter on the source grid that spans exactly one target cell (fractional area weights), sampled with point bilinear interpolation at the cell centres |

- At ratios ≤ 1 the box is a single pixel, so the method is plain bilinear
  interpolation; it never creates detail finer than the source.
- Valid-pixel values and the valid-area weight are filtered and interpolated
  separately; elevation = values / weight. A cell is valid only if valid pixels
  cover at least 50 % of it (`MIN_CELL_COVERAGE`), exactly as before, so NoData
  never leaks into elevations.
- The final sampling uses SciPy `map_coordinates` rather than GDAL `bilinear`:
  GDAL widens its bilinear kernel when downsampling, which on top of the box filter
  would smooth twice (observed during development: roughness similarity 0.48
  between the same terrain on rotated and unrotated grids).
- The grid rotation is measured at the footprint centre in the local frame;
  multiples of 90° count as aligned.
- Results carry `sampling = "interpolated"`; near-native cases still report
  `NEAR_NATIVE_INTERPOLATED` (wording updated to "bilinearly interpolated").

## Verification (synthetic controls and the real references)

Native-pixel descriptors vs the grid an analysis actually uses (Earth DEM finer
than the reference, common cell = reference spacing):

| Reference | Mean roughness native → 0.3 → 0.4 | Native vs processed total, 0.3 → 0.4 |
|---|---|---|
| Shackleton | 1.40 → 5.09 → 1.12 m | 0.771 → 0.935 |
| Mons Mouton | 1.17 → 1.83 → 1.02 m | 0.878 → 0.949 |
| Gale | 6.74 → 5.96 → 6.10 m | 0.984 → 0.987 |
| Amazonis | 0.38 → 0.33 → 0.34 m | 0.958 → 0.961 |

Self-similarity through the full pipeline (reference DEM re-hosted on an Earth
UTM grid and analysed against itself):

| Reference | 0.3 | 0.4 |
|---|---|---|
| Shackleton | 0.750 | 0.981 |
| Mons Mouton | 0.796 | 0.984 |
| Gale | 0.983 | 0.986 |
| Amazonis | 0.958 | 0.960 |

Unchanged behaviour (bit-identical or within 0.0004): the Gale golden value for
the synthetic Earth fixture (0.3962021713268066, genuine aligned downsampling),
constant offsets, scale/offset-encoded and feet-declared inputs, input-resolution
invariance (25/50/100 m), NoData handling and determinism. The same synthetic
Earth DEM now scores 0.4015 (was 0.2214) against Shackleton and 0.5356 (was 0.3883)
against Mons Mouton: these differences come from removing the artefact, not from
any tuning, and scores from 0.3 and 0.4 must not be compared.

Regression tests: `tests/test_resampling_0_4.py` (rotation detection, no roughness
inflation, native-vs-processed self-similarity > 0.90, monotonic behaviour at 2× and
3× downsampling, Mars not degraded relative to 0.3, rotated vs unrotated Earth DEMs
> 0.95, NoData and scale/offset on the interpolated path, API reports 0.4).

## Remaining limitations

- **Interpolation smoothing.** Resampling a rotated grid at ~1:1 must blend
  neighbouring pixels. Lunar reference roughness is now ≈ 15–20 % below the native
  pixels (1.40 → 1.12 m at Shackleton); pixel-scale white noise is attenuated more
  (≈ 40 % in a synthetic control). This is a physical consequence of resampling,
  not an artefact, and the reference is smoothed only once.
- **Support asymmetry.** When an Earth DEM is genuinely downsampled (area average)
  and the reference is interpolated at ~1:1, the two grids still have different
  effective smoothing. Self-similarity with a point-sampled Earth copy of
  Shackleton is 0.936 (vs 0.981 when both are interpolated).
- Unchanged from 0.3: unverified effective resolution of all references (LOLA
  effective resolution at Shackleton ranges 5.7–131.7 m), descriptors that ignore
  spatial arrangement and the sign of relief, scale-dependent scores that must not
  be ranked across references, and uncalibrated bins and weights.
