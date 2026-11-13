# Terra Analog

Terra Analog is a NASA Space Apps Challenge 2026 project being prepared for the November 14–15 hackathon. It will compare terrain characteristics of an uploaded Earth digital elevation model (DEM) with a selected reference region on Mars or the Moon.

**Status:** planning and documentation only. Application development starts November 14, 2026. This repository does not yet contain a runnable application.

## Project scope

[PROJECT-CONTEXT.md](PROJECT-CONTEXT.md) is the source of truth for project decisions. Users will upload one Earth DEM GeoTIFF, select a planet and a prepared planetary reference, and receive terrain similarity results. Global Earth scanning is outside scope.

MVP terrain metrics are relative relief, slope distribution and surface roughness. Each successful analysis returns a score from 0 to 1 for each metric, a `total_similarity` from 0 to 1, and any warnings. The 0–1 range is an API convention (`1.0` = maximum, `0.0` = minimum terrain similarity), not a scientifically validated calculation; the score formula, normalization and weights are not yet approved. Scores describe geometric terrain similarity only. They do not indicate habitability, base suitability, environmental equivalence or mission suitability.

Terrain morphology is deferred beyond the MVP. Earth aridity and lithology are deferred optional features that are not approved for the MVP and require separate approval.

## Planned technology stack

| Component | Confirmed technology | Responsibility |
| --- | --- | --- |
| Frontend | React | Selection, upload, results, errors and warnings |
| Backend | FastAPI | Validation, processing, similarity and API responses |
| Raster processing | Rasterio | DEM preprocessing and resolution harmonization |
| Numerical analysis | NumPy and SciPy | Terrain feature extraction and calculations |

Versions, frontend tooling, deployment, and runtime requirements are not yet selected. The confirmed analysis endpoint is `POST /analyze` with fields `file`, `planet` and `reference_id`. Approved mock responses are in [data/examples/](data/examples/).

## Repository structure

```text
.
├── .github/pull_request_template.md
├── backend/README.md
├── frontend/README.md
├── data/
│   ├── README.md
│   └── examples/
│       ├── analyze-success.json
│       └── analyze-error.json
├── docs/
│   ├── architecture.md
│   ├── api-contract.md
│   └── methodology.md
├── AGENTS.md
├── CLAUDE.md
├── CONTRIBUTING.md
├── PROJECT-CONTEXT.md
├── README.md
├── .gitignore
└── LICENSE
```

The backend and frontend directories contain planning documentation only.

## Documentation

- [Project context](PROJECT-CONTEXT.md): authoritative scope and responsibilities.
- [Contributing and readiness checklist](CONTRIBUTING.md): preparation rules, branches and collaboration.
- [Agent instructions](AGENTS.md) and [Claude Code notes](CLAUDE.md): rules for AI coding agents.
- [Backend plan](backend/README.md) and [frontend plan](frontend/README.md): ownership and development checklists.
- [Data plan](data/README.md): provenance, reference preparation and storage.
- [Architecture](docs/architecture.md): boundaries and processing flow.
- [API contract](docs/api-contract.md): approved request fields, MVP mock responses and unresolved questions.
- [Methodology](docs/methodology.md): MVP metrics, score convention, deferred features and validation.

Documentation labels approved decisions separately from proposals and open questions. Proposals require team agreement before implementation.

## Git workflow

Backend work happens on `backend--dev` and frontend work on `frontend--dev`. Pull requests target `main`, and humans approve all merges. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Repository software and documentation are provided under the [MIT License](LICENSE). Dataset usage rights and attribution must be checked separately for each source.
