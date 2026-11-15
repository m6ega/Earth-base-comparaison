# Scientific corrections: methodology 0.3-proposal

Scope: isolated branch science/fixes-20261115, based on committed backend
2708dbb349146d8f3995687a057296c6c61c5234. No frontend, reference asset,
source DEM, API field, metric weight or planetary geometry changes.
Older root methodology/project documents predate the implemented universal
engine. This records the explicitly authorized changes without silently
rewriting those shared specifications.

## Elevation decoding

Physical height in metres = (raw DN * band scale + band offset) * unit factor.
The source GDAL valid-data mask is applied before decoding. NoData is not
scaled into a plausible height; valid zero elevations remain valid. Internal
mask precedence remains GDAL's existing behavior. Nonfinite encoding metadata
and arithmetic overflow fail validation. Plausibility limits apply to physical
metres. Identity encoding preserves ordinary inputs. Runtime reference assets
still require identity encoding; no reference was rewritten.

Source: https://gdal.org/en/stable/api/gdalrasterband_cpp.html (GetScale,
GetOffset: RasterIO does not apply them).

## Minimal distribution change

For existing edges b, define c_i=(b_i+b_(i+1))/2. For a finite value x between
adjacent centers c_i and c_(i+1), assign masses
w_i=(c_(i+1)-x)/(c_(i+1)-c_i) and w_(i+1)=1-w_i. Outside the center range,
assign all mass to the nearest endpoint. Normalize by the finite sample count.
Each value contributes exactly unit mass; no pseudocount or new bandwidth is
introduced. This continuous piecewise-linear assignment replaces only the
hard scoring histogram. It is an explicit provisional estimator, not a claim
that prior bins or their midpoints are scientifically optimal.

Jensen-Shannon distance remains sqrt((KL_2(P||M)+KL_2(Q||M))/2), M=(P+Q)/2.
Per-metric similarity remains 1-distance; total remains the equal-weight mean.
The implementation sums scipy.special.rel_entr terms before taking the square
root. A negative numerator within 64 float64 machine epsilons is treated as
zero roundoff; larger negatives/nonfinite values fail. Near-equal soft masses
exposed scipy.spatial.distance.jensenshannon returning NaN from cancellation.
Independent closed-form and random-distribution tests verify the same equation.
This guard affects floating-point noise, not a scientific score threshold.

The slope chart continues to return true counts in the original intervals;
soft masses are not misrepresented as those counts. SOFT_HISTOGRAM_SCORING
explains the distinction in every result. All three metric distributions use
the same assignment policy. Existing tests of hard chart counts are retained;
scale-comparison tests now exercise the actual soft scoring representation.

## Controlled evaluation and safeguards

Regression tests cover:
- DN=1000, scale=.5, offset=10 -> 510 metres, including metre, international
  foot and US-survey-foot conversion, aligned and area-averaged sampling.
- Raw NoData, internal masks, valid decoded zero, negative/zero scales,
  invalid metadata, overflow and plausibility after decoding.
- Exact independent linear-mass oracle; finite normalized mass; empty/one-bin
  distributions; endpoints; continuity at every existing center and boundary.
- Slopes .999999 and 1.000001 degrees: hard score 0, soft score >.99999.
  A 25-degree negative control still has zero slope similarity.
- Same-bin .6/.9 values: hard score 1, soft score below 1, demonstrating that
  assignment does not merely raise every score.
- Identity and constant vertical offsets; z versus -z still indistinguishable.
- Flat pairs still score 1, but both sides are explicitly flagged.
- API uses soft scores while preserving hard chart counts and warning shapes.

No real-terrain ranking calibration has been performed. Numerical success is
not evidence of analog validity. No target score was used to tune bins/weights.

FLAT_TERRAIN retains the Earth code; REFERENCE_FLAT_TERRAIN flags the reference.
The existing max-local-relief <1 m criterion is unchanged. LOW_INFORMATION_TERRAIN
identifies any exact single-bin chart distribution on either side; it does not
pretend to measure statistical confidence or diagnose every low-information case.
DESCRIPTOR_SIMILARITY_ONLY explains that distribution agreement is not geological
or morphological equivalence. CROSS_REFERENCE_SCALE_CAUTION warns on every
comparison that adaptive physical scales cannot support unqualified ranking.

## Remaining scientific limitations

Soft assignment smooths the distribution representation, not the DEM. Nonuniform
bin spacing creates nonuniform smoothing: the very broad terminal relief and
roughness bins remain especially coarse. Endpoint clamping discards distinctions
outside the center range. Midpoints and the original edges require real-data
validation; this change addresses continuity, not calibration. Hard chart counts
can still jump at an edge. Version 0.2 and 0.3 scores are not interchangeable.

Hills/depressions and different spatial arrangements can retain identical
unsigned descriptors. Effective resolution and point-versus-area support remain
unmatched in places. Crop and physical neighborhood size depend on the selected
reference. Missing-data patterns can bias distributions. Gale's zero-value mask
question is unresolved and its assets were not changed. Existing registry
compatibility covers Gale, Mons Mouton and Shackleton; uncommitted Amazonis is
intentionally absent from this worktree and was not registered or modified.

## Safe later integration (not executed)

1. The owner completes the existing merge and commits/preserves Claude's UI work
   in the original checkout. Do not stash/reset/discard it as part of this task.
2. Verify original checkout is frontend--dev, no MERGE_HEAD, and clean staged/
   tracked state. Review backend changes since the worktree base.
3. Review this single scientific commit; cherry-pick its hash only after the
   above conditions and human authorization. If conflicts occur, stop for a
   deliberate backend review rather than accepting either side wholesale.
4. Re-run full backend pytest and frontend/backend integration on the combined
   code. Restart backend workers to clear old methodology caches.
5. Review real-DEM benchmark results before claiming cross-reference ranking.
   Nothing is pushed automatically.

## Recorded validation

Initial full run: 166 passed, one failed because the Gale integration test
pinned the old methodology-0.2 score. Its golden value was explicitly versioned
and updated from 0.3584422608885516 to 0.3962021713268066 for the same synthetic
Earth fixture. No estimator parameters were changed in response to that score.
The existing scale, polar, cache, registry and API tests passed unchanged apart
from using the intentional new scoring representation in comparison helpers.
A dedicated near-equal-vector roundoff regression was also added.

Numerical edge-case measurement: .999999 versus 1.000001 degrees gives
slope similarity 0.9999983013445296 (previous hard assignment: 0).
Relief similarity is 0.9999973281281326; roughness similarity is 1.
The same 25-degree negative control remains disjoint in slope support.
Flat/flat and z/-z remain 1, with the limitations explicitly disclosed.

Final full-suite validation: **168 passed, 0 failed**, 91.14 seconds.
Command (backend directory): python -B -m pytest -q -p no:cacheprovider.
Includes actual Gale, Mons Mouton and Shackleton API/registry/polar/cache tests,
22 new scientific regressions, and existing analytical mathematics tests.
Nine warnings: the existing Starlette/httpx deprecation and unreferenced PNG
preview reads (not DEM georeferencing failures). A transient test-collection
encoding error was corrected by normalizing the edited file to UTF-8 before
this final run. No real observational Earth benchmark or browser test was run.
Original frontend files, index, HEAD and MERGE_HEAD were hash-checked unchanged;
main remained b71737a48224f40301d0397e5786e4d03d0325a9.
