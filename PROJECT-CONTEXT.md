# Project Context — Terra Analog

## Project Goal

Build a web application that compares terrain
characteristics of Earth locations with selected
reference regions on Mars or the Moon.

## Product Scope

Users upload one Earth DEM file (GeoTIFF) and select
a planet and a prepared planetary reference.

The application processes both datasets
and calculates terrain similarity.

No global Earth scanning.

## Architecture

- React frontend
- FastAPI backend
- Rasterio for DEM processing
- NumPy and SciPy for numerical calculations

## Backend Responsibilities

- File validation
- DEM preprocessing
- Resolution harmonization
- Terrain feature extraction
- Similarity calculations
- Validation, preparation, storage and integration
  of planetary reference data
- Optional enrichment handling
- API responses

## Frontend Responsibilities

- User interface
- Planet selection
- Reference selection
- DEM upload
- Results visualization
- Error and warning display

## Terrain Metrics

MVP terrain similarity metrics:

1. Relative relief
2. Slope distribution
3. Surface roughness

Future extension (deferred beyond the MVP):

4. Terrain morphology (for example, a topographic
   position index, TPI)

Terrain morphology was part of the initial metric list.
It remains scientifically relevant but is not part of
the MVP similarity score.

## Optional Enrichment

Earth aridity and lithology may be reported as
optional context.

- They do not contribute to the terrain similarity score.
- Missing enrichment data must not block terrain analysis.

## API

POST /analyze

Request fields: `file` (one Earth DEM GeoTIFF),
`planet` (`mars` or `moon`), `reference_id`
(selected prepared planetary reference).

See docs/api-contract.md.

## Team Responsibilities

Backend Lead:
- backend/
- Terrain processing
- Similarity algorithm
- API
- Validates, prepares, stores and integrates
  planetary reference data

Frontend & Data Lead:
- frontend/
- User interface
- Research of NASA planetary reference data
- Documentation of reference data provenance

## Git Workflow

- `backend--dev`: backend work
- `frontend--dev`: frontend work
- `main`: reviewed integration
- Pull requests target `main`.
- Humans approve pull requests and merges.
- AI agents never merge automatically.

## Development Rules

- Keep backend and frontend responsibilities separate.
- Follow the API contract.
- Avoid unnecessary dependencies.
- Do not rewrite working code without a reason.
- Test changes before committing.
- Never commit secrets or API keys.

## AI Coding Rules

- Work only on the requested task.
- Do not modify unrelated files.
- Explain important changes.
- Keep implementation simple.
- Do not introduce unnecessary abstractions.
- Follow the existing project architecture.
- See AGENTS.md.

## Current Status

Planning and preparation only.
No application code before November 14, 2026.
Application development starts at the hackathon.
