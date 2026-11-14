# Terra Analog

Terra Analog compares the **terrain geometry** of an Earth elevation model (a GeoTIFF
DEM you upload) with NASA-derived elevation models of regions on Mars and the Moon.
It reports how closely local relief, slope and surface roughness are distributed, as
an experimental similarity index from 0 to 100.

It was built for the NASA Space Apps Challenge 2026 (14–15 November 2026).

**Intended users:** students, educators, science communicators and researchers who
want an exploratory, transparent comparison between an Earth landscape and planetary
terrain. It is a research prototype, not an operational or decision-making tool.

> **What the score means:** similarity measures statistical resemblance of terrain
> descriptor distributions. It is **not** a probability, a confidence level, a
> percentage of geological equivalence, or a habitability, safety or landing-site
> assessment. Scores from different references are computed at different physical
> scales and must not be ranked against each other.

## Status

Release candidate on `frontend--dev` (methodology `0.3-proposal`). Tested
capabilities are listed under [What has been verified](#what-has-been-verified);
everything in [Limitations and future work](#limitations-and-future-work) is not
implemented.

## Quick start (local)

Requirements: Python 3.14 (3.12 also has wheels for every dependency). No system
GDAL or PROJ is needed: `rasterio` and `pyproj` wheels bundle them.

```bash
cd backend
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1    Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q                      # full test suite
cd ..
python backend/check_references.py      # validate all reference registrations
python -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

Open <http://127.0.0.1:8000>. The backend serves the website and the API from the
same origin. Upload an Earth GeoTIFF, choose Mars or the Moon and a reference, then
click **Analyze Terrain**.

Frontend-only editing with VS Code Live Server (port 5500) also works:
`frontend/config.js` then sends API requests to port 8000 on the same host.

For production deployment (Docker or a plain Python host), see
[DEPLOYMENT.md](DEPLOYMENT.md).

## How it works

1. **Upload validation:** GeoTIFF signature and extension, size (≤ 50 MB), raster
   dimensions, projected or geographic CRS on an Earth ellipsoid, NoData, band
   scale/offset decoding, plausible elevation range, and vertical units.
2. **Vertical units:** units declared in the file always win (feet are converted to
   metres). Only files that declare no units are read as metres by default; the
   result then carries a visible `VERTICAL_UNITS_ASSUMED` notice.
3. **Harmonization:** the Earth DEM and the selected reference are resampled to a
   common ground resolution and an equal central footprint.
4. **Descriptors:** local relief (5 × 5 window), slope in degrees, and surface
   roughness (RMS residual from a local plane, 3 × 3).
5. **Scoring (methodology 0.3):** each descriptor is summarised by a soft histogram
   (linear assignment between bin centres) and compared with a numerically
   stable base-2 Jensen–Shannon distance; `score = 1 − distance`. The total is the
   unweighted mean of the three scores.
6. **Warnings:** every response includes machine-readable cautions (comparison
   scale, low-information or flat terrain, unit handling, reference limitations).
   The website shows all of them and highlights condition-specific ones as
   *Scientific notes*.

Full method, thresholds and warning codes: [backend/README.md](backend/README.md)
and [backend/SCIENTIFIC-FIXES-0.3.md](backend/SCIENTIFIC-FIXES-0.3.md). Every
threshold and weight is a documented **proposal**, not a calibrated or validated
scientific standard.

## Planetary references

| ID | Body | Region | Source data |
|---|---|---|---|
| `mars-gale` | Mars | Gale Crater | NASA MGS MOLA MEGDR (MEG128, 128 px/°) |
| `mars-amazonis` | Mars | Amazonis Planitia | NASA MGS MOLA MEGDR v2.0, tile MEGT44N180HB |
| `moon-mons-mouton` | Moon | Mons Mouton | NASA LRO LOLA adjusted south-polar DEM, PGDA product 90 |
| `moon-shackleton` | Moon | Shackleton Crater | NASA LRO LOLA adjusted south-polar DEM, PGDA product 90 |

Each reference lives in `backend/references/<id>/` as `dem.tif`, `metadata.json`,
`preview.png` and an approval record `registration.json`. The registration pins
SHA-256 hashes of the three assets, and the API refuses any reference whose
bytes differ. `.gitattributes` stores these files byte-for-byte so every checkout
on Windows, Linux and macOS validates. Adding a region on a supported body needs
only verified assets and a registration (see
[backend/PLANETARY-REFERENCES.md](backend/PLANETARY-REFERENCES.md)). Raw NASA
source products are never committed.

**Attribution:** Mars topography: NASA/MGS MOLA Science Team (D. E. Smith, GSFC),
MOLA Mission Experiment Gridded Data Records, PDS Geosciences Node.
Lunar topography: NASA LRO Lunar Orbiter Laser Altimeter team, NASA GSFC Planetary
Geodesy Data Archive (PGDA) product 90. Reference crops and previews were prepared
from these products without resampling; per-reference provenance and limitations
are recorded in each `metadata.json` and `registration.json`.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check: `{"status": "ok"}` |
| GET | `/references` | Registered references with `id`, `name`, `body`, `category`, `description`, `preview_url`, centre, grid spacing and limitations |
| POST | `/analyze` | Multipart: `file` (GeoTIFF), `reference_id`, optional `vertical_unit`, optional `vertical_unit_fallback` |

Successful analyses return `is_mock: false`, `total_similarity` and `scores` in
[0, 1], an Earth preview, slope-distribution chart data and `warnings`. Errors
use `{"status": "error", "error": {"code", "message"}}` and never expose server
paths or stack traces. Contract: [docs/api-contract.md](docs/api-contract.md).

## Privacy and uploaded files

- Uploaded GeoTIFFs are written to a temporary directory under a fixed name,
  processed for that request only, and deleted when the request finishes
  (including on errors). Nothing is stored, logged or shared.
- The client's file name is never used as a path and is not logged.
- The service sets no cookies and needs no accounts or secrets.

## What has been verified

On the release candidate (see the commit history for details):

- Backend test suite (including scientific regression tests for scale/offset
  decoding, soft histogram continuity at every bin edge, Jensen–Shannon
  round-off, unit handling, reference integrity and portability, deployment
  behaviour).
- All four references validated from a fresh clone that uses Linux line-ending
  behaviour, and analysed through HTTP and through a real browser (Chrome) against
  a production-style server: upload, planet and reference switching, analysis,
  warnings, error and retry states, stale-response protection, mobile layouts and
  reduced motion.
- GitHub Actions runs the test suite on Linux and builds and smoke-tests the Docker
  image on every push to `frontend--dev`.

## Limitations and future work

- The methodology is a proposal: thresholds, bins and equal weights are not
  calibrated against expert analog judgements. No accuracy is claimed.
- Effective resolution of the reference DEMs is not verified; grid spacing is
  not effective resolution. Upstream gridding and interpolation are inherited.
- Scores depend on the comparison scale (resolution and footprint), which depends
  on both inputs. Do not rank scores across references or scales.
- Flat or low-information terrain can produce misleadingly high similarity; such
  cases are flagged but not excluded.
- Synthetic test DEMs were used for automated tests; no curated set of real
  Earth-analog benchmarks has been evaluated yet.
- Future work: more references (registration is data-only), calibration studies,
  and an optional elevation-unit selector for advanced users.

## Repository structure

```text
backend/            FastAPI app, analysis pipeline, references/, tests/
frontend/           Static HTML/CSS/JS website (served by the backend)
docs/               API contract, architecture, methodology, UI concept
mars-source/        Provenance labels and preparation script for Gale Crater
data/examples/      Mock API fixtures (not scientific results)
Dockerfile          Single-service production image
DEPLOYMENT.md       Deployment, configuration and verification guide
```

## Contributing and branches

`frontend--dev` is the active development branch (website and backend together);
`main` is the stable branch and changes only through reviewed pull requests. See
[CONTRIBUTING.md](CONTRIBUTING.md), [PROJECT-CONTEXT.md](PROJECT-CONTEXT.md) and
[AGENTS.md](AGENTS.md).

## License

Software and documentation: [MIT License](LICENSE). NASA data products are used
under NASA's open data policy with the attribution above.
