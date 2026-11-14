# Project Context — Terra Analog

This file is the authoritative source for approved
project decisions. Other documents link here instead
of restating these decisions. If another document
conflicts with this file, this file wins; report the
conflict.

## Project Goal

Build a web application that compares the terrain
geometry of an uploaded Earth elevation model with
a selected NASA Mars reference region.

## MVP Scope

- Users upload one Earth elevation GeoTIFF and select
  one prepared Mars reference.
- Mars references come from NASA Mars Orbiter Laser
  Altimeter (MOLA) elevation data.
- Mars only. The Moon is out of scope for the MVP.
- Gale Crater is the required primary reference.
- Gusev Crater is optional and is added only after
  the first working comparison.
- No global Earth scanning.

The Gale Crater reference (`mars-gale`) is prepared
and its source and geospatial metadata are recorded
in `backend/references/mars-gale/metadata.json`.
Gusev Crater is not prepared; see data/README.md.

## Stack

- Frontend: React + Vite
- Backend: Python + FastAPI
- Geospatial processing: Rasterio + NumPy
- SciPy is optional, not a mandatory dependency.

Package versions, deployment and hosting are not
yet selected.

## Metrics

1. Relative relief
2. Slope distribution
3. Surface roughness
4. Overall geometric similarity score
   (`total_similarity`), derived from the three
   metric scores

Scores use a 0–1 range as an API convention:
`1.0` is maximum and `0.0` minimum terrain
similarity. Formulas, normalization and weights are
not approved; see docs/methodology.md.

Deferred beyond the MVP: terrain morphology (for
example, TPI). Earth aridity and lithology are
deferred optional features that require separate
approval; if approved later, they must not
contribute to the similarity score, and missing data
for them must not block terrain analysis.

## Scientific Meaning

- Scores describe terrain geometry similarity only.
  They do not indicate habitability, base
  suitability, environmental equivalence or mission
  suitability, and they are not probabilities.
- Earth and Mars data must not be treated as
  directly comparable until physical extent,
  effective resolution, coordinate systems, vertical
  units and NoData handling have been checked.
  Unresolved comparability issues are reported as
  warnings.

## Data Ownership

- The backend stores and processes Mars GeoTIFFs.
  It owns the Mars DEM and the reference metadata,
  stored under `backend/references/<reference_id>/`
  (`dem.tif`, `preview.png`, `metadata.json`).
- The backend serves the prepared Mars preview to
  the frontend. The frontend does not store or
  analyze the Mars DEM.
- Source provenance for a reference comes from its
  verified `metadata.json`, not from assumptions.
- Mars terrain features may be precomputed and
  cached on the backend.
- Cached Mars features must be recomputed whenever
  metric definitions or the processing scale change.
- The frontend performs no scientific calculations.
  It displays backend results.
- Large raw DEM files (including raw NASA source
  files), uploads and generated rasters are excluded
  from Git. The one exception is the small validated
  `backend/references/mars-gale/dem.tif`; see
  data/README.md.

## API

MVP endpoints: `GET /health`, `GET /references` and
`POST /analyze`. `POST /analyze` accepts `file`
(Earth GeoTIFF) and `reference_id` (Mars reference).
There is no `planet` field. The MVP interface shows
only the Gale Crater reference, with no selector;
see docs/ui-concept.md.

docs/api-contract.md defines the response schema.
The frontend-facing fields there are pending review
by the Frontend & Data Lead. Files in data/examples/
are mock test fixtures only, never scientific
results.

## Responsibilities

Backend Lead + Claude:
- Architecture and API
- DEM processing and metrics
- Backend validation
- Storage, preparation and caching of Mars
  reference data (`backend/`)

Frontend & Data Lead + Codex:
- UI concept ([docs/ui-concept.md](docs/ui-concept.md))
  and React frontend (`frontend/`)
- NASA MOLA source research
- Reference data provenance documentation
  (data/README.md)

Final decisions and all merges require human
approval. AI agents stay within their owner's area.

## Git Workflow

- `backend--dev`: backend work
- `frontend--dev`: frontend work
- `main`: reviewed integration; must remain runnable
  once implementation begins
- `docs/<topic>`: short-lived documentation branches
- Pull requests target `main`. Humans approve pull
  requests and merges. AI agents never merge.

The mandatory phase workflow is in CONTRIBUTING.md.

## Development Rules

- Keep backend and frontend responsibilities separate.
- Follow the API contract.
- Avoid unnecessary dependencies and abstractions.
- Do not rewrite working code without a reason.
- Test changes and report results before each PR.
- Never commit secrets, API keys, virtual
  environments, node_modules or large DEMs.

Agent-specific rules: AGENTS.md.

## Status

- Pre-hackathon preparation (before November 14,
  2026) produced documentation only: repository
  setup, development guidelines and an initial mock
  API contract (PRs #1–#3). That contract allowed
  Mars or Moon references and a `planet` field; both
  are superseded by this revision.
- Phase 0 (November 14, 2026): documentation and
  architecture revision. No application code.
- Application implementation starts in Phase 1,
  after Phase 0 is approved and merged.
