# Terra Analog

Terra Analog is a NASA Space Apps Challenge 2026 project (hackathon November 14–15, 2026). It compares the terrain geometry of an uploaded Earth elevation GeoTIFF with a NASA Mars MOLA reference region: Gale Crater, and optionally Gusev Crater. It reports relative relief, slope distribution, surface roughness and an overall geometric similarity score.

Scores describe terrain geometry only. They do not indicate habitability or base suitability.

**Status:** Phase 0 (documentation and architecture revision). There is no runnable application yet. Pre-hackathon preparation produced documentation only (PRs #1–#3). Implementation starts in Phase 1.

## Stack

React + Vite frontend; Python + FastAPI backend; Rasterio + NumPy processing (SciPy optional).

## Documentation

- [Project context](PROJECT-CONTEXT.md): **authoritative** scope, decisions and responsibilities.
- [Contributing](CONTRIBUTING.md): the mandatory phase workflow, branches and validation.
- [Agent instructions](AGENTS.md) and [Claude Code notes](CLAUDE.md): rules and ownership boundaries for AI agents.
- [API contract](docs/api-contract.md): `GET /health`, `GET /references`, `POST /analyze` and the response schema.
- [UI/UX specification](docs/ui-concept.md): the approved frontend concept for Phase 1 (read it before implementing the frontend).
- [Architecture](docs/architecture.md): components, flow and feature cache.
- [Methodology](docs/methodology.md): comparability checks and candidate metric definitions.
- [Backend](backend/README.md), [frontend](frontend/README.md) and [data](data/README.md) plans.
- [data/examples/](data/examples/): mock API fixtures, not scientific results.

## Repository structure

```text
.
├── .github/pull_request_template.md
├── backend/
│   ├── README.md
│   └── references/mars-gale/   dem.tif, preview.png, metadata.json
├── frontend/README.md
├── data/
│   ├── README.md
│   └── examples/   health.json, references.json, analyze-success.json, analyze-error.json
├── docs/           api-contract.md, architecture.md, methodology.md, ui-concept.md
├── AGENTS.md, CLAUDE.md, CONTRIBUTING.md, PROJECT-CONTEXT.md, README.md
├── .gitignore
└── LICENSE
```

## Git workflow

Backend work happens on `backend--dev` and frontend work on `frontend--dev`. Pull requests target `main`, and humans approve all merges. After each merge, `main` is tested and both development branches are synced with it. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Repository software and documentation use the [MIT License](LICENSE). Usage rights and attribution for each dataset are checked separately.
