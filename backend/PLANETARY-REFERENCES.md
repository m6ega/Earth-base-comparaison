# Planetary reference engine: backend/frontend handoff

This backend extension implements the user's Mars/Moon scope on `frontend--dev`.
Older root project/UI documents still describe the Mars-only initial scope. No
frontend changes or changes to those shared specifications were made here.

## Runtime registration and trust boundary

Each `backend/references/<id>/` has `dem.tif`, `metadata.json`, `preview.png`,
and `registration.json`. The first three remain the scientific runtime assets;
the fourth is an explicit approval record. A raw directory is never selectable.
The record uses schema_version=1; reference_id, enabled and approved (strict
booleans), body, name, category (string/null), description, effective_resolution_m
(positive finite number/null), effective_resolution_evidence (string/null),
limitations (string array), and sha256 (exactly the three runtime filenames with
lowercase SHA256 digests). Unknown approval fields are rejected.

`reference-bodies.json` contains supported body models with a name and positive
semi_major_m/semi_minor_m. Mars and Moon spheres use their source CRS radii.
Adding a region on a supported body requires only its verified assets and approval
record, not Python changes. A new planetary body requires a scientifically reviewed
body configuration, datum/unit interpretation and geometry tests; arbitrary bodies
are not automatically endorsed. Approval files are trusted operator configuration,
not cryptographic signatures or uploadable API data.

Metadata supports existing legacy fields: planet, region, source, center with
latitude_planetocentric/longitude_positive_east, elevation with unit/reference/
minimum/maximum/mean, raster with width/height/resolution_metres/nodata/
valid_pixels/nodata_pixels, and coordinate_system with projection/crs_wkt.
Additional provenance fields are retained. Required fields have strict types and
finite numeric values. Runtime references must be projected in metres, elevations
in metres, with declared finite NoData, identity scale/offset, correct body model,
matching dimensions/statistics/masks/centre and a readable PNG. Source attribution
and scientific approval still require human review; software cannot prove provenance
from metadata alone. The three supplied datasets were checked against their existing
source audit and content checksums; their raster/preview/metadata bytes are unchanged.

The legacy Mons Mouton `mars_radius_metres: null` is treated as inapplicable;
its actual body model is verified against its lunar WKT and body configuration.
No lunar value is inserted into a Mars-specific field.

Disabled or invalid entries are omitted from GET /references with server diagnostics.
An explicit request for a known but disabled/corrupt entry returns 500
REFERENCE_UNAVAILABLE. Unknown or unsafe IDs return 400 UNKNOWN_REFERENCE.
An unknown preview URL returns 404. Identifiers are looked up in the discovered
registry, never joined from arbitrary request paths. Symlink/outside asset paths
are rejected. A registration with incorrect metadata is not partially exposed.

Reference files are hashed before each lookup; validated geometry is cached by
asset, approval and body-configuration fingerprint. Features also include this
fingerprint, physical grid and methodology version in their cache key. Replace
assets atomically, then approve new hashes; in-flight changes fail rather than
silently mixing reference generations. Modification during the validation read
itself is not an atomic filesystem snapshot; operators should avoid editing live
reference files in place.

## API: exact additive extension

GET /references returns:

    {"is_mock": false, "references": [Reference, ...]}

Reference fields (same object under POST success.reference):

| Field | Type / meaning |
| --- | --- |
| id | string, opaque ID to submit |
| name | string, display name |
| dataset | string, source dataset label |
| preview_url | string, resolve relative to configured API base |
| effective_resolution_m | positive number or null, never inferred from pixel spacing |
| body | string, lowercase configured body key (`mars`, `moon`) |
| category | string or null |
| description | string |
| center | object: latitude_planetocentric, longitude_positive_east, in degrees |
| grid_spacing_m | two numbers: measured centre ground spacing along source pixel axes |
| elevation_unit | `metres` |
| elevation_datum | string from validated metadata |
| limitations | array of scientific limitation strings |
| dem_sha256 | content SHA256 of the actual reference DEM |
| version | fingerprint of all runtime assets, approval and body configuration |

POST /analyze remains multipart: file and reference_id; the existing optional
vertical_unit override for Earth uploads is preserved. Do not send a planet field.
Approved supplied IDs: mars-gale, moon-mons-mouton, moon-shackleton.
No Content-Type override is needed when sending browser FormData.

Success retains status, is_mock=false, reference, total_similarity, scores
(relative_relief, slope_distribution, surface_roughness), earth_preview_url,
charts.slope_distribution and warnings. Scores remain finite 0..1 and are not
probabilities. Warnings are `{code,message}` objects. The slope chart retains unit,
bin_edges, earth and mars; NEW `reference` is the selected reference histogram.
`mars` is a deprecated alias equal to `reference` even for Moon, maintained solely
for old clients. New clients label the series using reference.body/name, never the
legacy field name. The reference.preview_url always selects the actual reference.
The top-level success fields are unchanged.

Errors retain `{status:"error",error:{code,message}}`. Existing upload validation
statuses are unchanged. Display actual messages and never substitute mock results.

Frontend state handoff (implementation belongs to teammate): load the selector
from GET /references, group by body, use id as value. On reference change clear
old scores/previews/warnings immediately but retain the selected Earth File.
Abort or disregard in-flight results using a monotonically increasing request
counter plus captured reference ID; accept a result only if both still match the
current request. Disable duplicate submissions. Unavailable selections require
refreshing GET /references and a new explicit analysis. Never relabel an old
result as a newly selected planet.

## Geometry and science

The same feature definitions, histogram bins, Jensen-Shannon distance and weights
remain unchanged; methodology 0.2 near-native one-to-one sampling is preserved.
Each dataset uses its own geodetic CRS and local AEQD metric frame. The old blanket
89-degree rejection is replaced by finite/invertible coordinate checks, independent
geodesic pixel-distance verification, finite outline/extent checks and deterministic
longitude at the exact pole. Pixel axes are measured as Cartesian displacements,
not degrees or longitude differences. Polar stereographic grid scale is not assumed
true everywhere. Round-trip and distance tests cover -85, -89, -89.67, -89.9999 and
-90 degrees, as well as existing Gale checks.

The common scale is the maximum of measured native spacings and any independently
verified scalar effective resolutions. Both arrays use equal cells and nominal
metre spacing/footprint, preserving the existing 1% near-native safeguard tolerance.
Local AEQD has residual transverse distortion away from the centre; equality is
local-grid equality, not a claim of exactly equal geodesic cell area everywhere.
Large/extreme footprints beyond the validated datasets need dedicated tests.

No new arbitrary Moon elevation bounds were invented: a checksum-verified reference
uses its measured valid elevation range during harmonization; Earth uploads retain
the existing scientific validation limits. These reference extrema are integrity
bounds, not a new planetary science model.

The lunar EFFRES products vary spatially; their median is NOT treated as a globally
valid effective resolution. These entries retain null scalar effective resolution
and an explicit warning. No additional terrain detail is invented. Source gridding,
interpolation, uncalibrated methodology and unequal data quality remain limitations.

## Reproduce checks / run

From backend with the existing environment (or Python 3.14 and
`pip install -r requirements-dev.txt`):

    python -m pytest tests -q
    python -m uvicorn app:app --host 127.0.0.1 --port 8000

Submit the SAME synthetic_earth.tif with each of the three reference IDs. It is a
synthetic surface, not an Earth observation. The backend README documents how to
regenerate it. A real observational Earth DEM was not found in this checkout.

Track all three runtime files plus registration.json for each prepared reference,
reference-bodies.json, backend source/tests/docs. Narrow .gitignore exceptions now
allow the two prepared lunar DEMs; raw-moon-data remains excluded. No staging,
committing or pushing is performed by this task.
