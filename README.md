# Terra Analog

Terra Analog is a NASA Space Apps Challenge 2026 project being prepared for the November 14–15 hackathon. It will compare terrain characteristics of an uploaded Earth digital elevation model (DEM) with a selected reference region on Mars or the Moon.

**Status:** planning and documentation only. Application development starts November 14, 2026. This repository does not yet contain a runnable application.

## Project scope

[PROJECT-CONTEXT.md](PROJECT-CONTEXT.md) is the source of truth for project decisions. Users will upload an Earth DEM, select a planetary reference region, and receive terrain similarity results. Global Earth scanning is outside scope.

Confirmed initial metrics are relative relief, slope distribution, surface roughness, and terrain morphology. Exact metric definitions and scoring remain open. Similar terrain does not establish environmental equivalence or mission suitability.

## Planned technology stack

| Component | Confirmed technology | Responsibility |
| --- | --- | --- |
| Frontend | React | Selection, upload, results, errors and warnings |
| Backend | FastAPI | Validation, processing, similarity and API responses |
| Raster processing | Rasterio | DEM preprocessing and resolution harmonization |
| Numerical analysis | NumPy and SciPy | Terrain feature extraction and calculations |

Versions, frontend tooling, deployment, and runtime requirements are not yet selected. The confirmed analysis endpoint is `POST /analyze`; its detailed contract is a draft.

## Repository structure

```text
.
├── .github/pull_request_template.md
├── backend/README.md
├── frontend/README.md
├── data/README.md
├── docs/
│   ├── architecture.md
│   ├── api-contract.md
│   └── methodology.md
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
- [Backend plan](backend/README.md) and [frontend plan](frontend/README.md): ownership and development checklists.
- [Data plan](data/README.md): provenance, reference selection and storage.
- [Architecture](docs/architecture.md): boundaries and processing flow.
- [Draft API contract](docs/api-contract.md): proposed interface and unresolved questions.
- [Methodology](docs/methodology.md): proposed metrics, comparison and validation.

Documentation labels confirmed decisions separately from proposals and open questions. Proposals require team agreement before implementation.

## License

Repository software and documentation are provided under the [MIT License](LICENSE). Dataset usage rights and attribution must be checked separately for each source.
