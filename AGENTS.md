# Instructions for AI agents

These rules apply to any AI coding agent working in this repository. They do not replace human review.

## Sources of truth

1. [PROJECT-CONTEXT.md](PROJECT-CONTEXT.md): approved scope, architecture and responsibilities.
2. [CONTRIBUTING.md](CONTRIBUTING.md): branch workflow, review and validation.
3. [docs/api-contract.md](docs/api-contract.md), [docs/architecture.md](docs/architecture.md), [docs/methodology.md](docs/methodology.md) and [data/README.md](data/README.md): approved decisions plus proposals that still need team agreement.

If documents conflict, follow PROJECT-CONTEXT.md and report the conflict instead of resolving it yourself.

## Approved decisions

- No application code before November 14, 2026. Until then, work is limited to documentation and repository preparation.
- `POST /analyze` accepts `file` (one Earth DEM GeoTIFF), `planet` (`mars` or `moon`) and `reference_id` (a selected, prepared planetary reference).
- MVP terrain similarity uses relative relief, slope distribution and surface roughness.
- A successful MVP response always includes `total_similarity` and per-metric `scores`, each a number from 0 to 1, plus `warnings`. Errors return `status: "error"` with `error.code` and `error.message`. The approved examples are [data/examples/analyze-success.json](data/examples/analyze-success.json) and [data/examples/analyze-error.json](data/examples/analyze-error.json).
- The 0–1 range is an API convention: `1.0` is maximum and `0.0` minimum terrain similarity. It is not a scientifically validated calculation. `warnings` is always an array; the schema of non-empty warnings is unresolved. The score formula, normalization and weights are not approved. Scores measure geometric terrain similarity only, not habitability or base suitability.
- Terrain morphology (for example, TPI) is deferred beyond the MVP.
- Earth aridity and lithology are deferred optional features, not approved for the MVP. Do not implement them, add enrichment fields to the API, approve their datasets, algorithms or schema, or factor them into terrain similarity without separate human approval.
- The Frontend & Data Lead researches NASA planetary reference data and documents provenance. The Backend Lead validates, prepares, stores and integrates the reference.
- Branches: `backend--dev` for backend work, `frontend--dev` for frontend work, `main` for reviewed integration. Pull requests target `main`.
- Humans approve pull requests and merges.

## Agent rules

- Work only on the requested task and the files it needs. Do not modify unrelated files.
- Never merge, approve pull requests, or push to `main`. Do not commit, push or open a pull request unless a human asks for that specific action.
- Never force-push shared branches or rewrite their history.
- Stage files by explicit path. Never use `git add .` or `git add -A`.
- Do not modify, stage, move or delete untracked files or nested repositories you did not create.
- Keep backend and frontend responsibilities separate; follow the API contract.
- Do not invent dataset properties, upload limits, formulas, weights, thresholds or scientific results. Mark proposals as proposals and list open questions.
- Never commit secrets, API keys, uploaded DEMs or large datasets.
- Report validation honestly, including checks you could not run.
