# Instructions for AI agents

These rules apply to every AI coding agent in this repository. They do not replace human review.

## Sources of truth

1. [PROJECT-CONTEXT.md](PROJECT-CONTEXT.md): approved scope, stack, data ownership and responsibilities. It is authoritative.
2. [CONTRIBUTING.md](CONTRIBUTING.md): the mandatory phase workflow, branches, review and validation.
3. [docs/api-contract.md](docs/api-contract.md): the endpoint and response schema.
4. [docs/ui-concept.md](docs/ui-concept.md): the approved frontend UI/UX specification.
5. [docs/architecture.md](docs/architecture.md), [docs/methodology.md](docs/methodology.md) and [data/README.md](data/README.md): design and proposals still needing agreement.

If documents conflict, follow PROJECT-CONTEXT.md and report the conflict instead of resolving it yourself.

## Ownership boundaries

| Agent | Works with | Area | Branch |
| --- | --- | --- | --- |
| Claude | Backend Lead | `backend/`: architecture, API, DEM processing, metrics, backend validation, Mars reference storage and caching | `backend--dev` |
| Codex | Frontend & Data Lead | `frontend/`: UI concept and React frontend; MOLA source research and provenance in `data/README.md` | `frontend--dev` |

- Do not modify the other agent's area. Changes to shared files (the API contract, `data/examples/`, PROJECT-CONTEXT.md) need review from both leads.
- The frontend performs no scientific calculations, and backend science must not be duplicated there.
- Final decisions belong to humans.

### Frontend implementation (Codex)

Codex must read and follow [docs/ui-concept.md](docs/ui-concept.md) and [docs/api-contract.md](docs/api-contract.md) before implementing the frontend, and must also read PROJECT-CONTEXT.md, AGENTS.md and CONTRIBUTING.md.

- UI behavior must match the approved UI specification. Significant design changes require human approval.
- Do not change the API contract without cross-team agreement. Report conflicts between the UI specification and the contract instead of changing either silently.
- Do not modify backend-owned files without permission.
- Start only when the [Phase 1 readiness criteria](frontend/README.md#phase-1-readiness) are met, and do not build later-phase features early.

## Git rules

- Follow the [phase workflow](CONTRIBUTING.md#phase-workflow-mandatory).
- Never merge, approve pull requests or push to `main`. Commit, push or open a pull request only when a human asks for that specific action.
- Never force-push or rewrite shared history.
- Stage files by explicit path. Never use `git add .` or `git add -A`.
- Never commit `.venv`, `node_modules`, large DEMs, uploads, generated rasters, secrets or API keys.
- Do not modify, stage, move or delete untracked files or nested repositories you did not create.

## Work rules

- Work only on the requested task and the files it needs.
- Follow the API contract. Keep fixtures in `data/examples/` marked `is_mock: true`, and never present mock values as scientific results.
- Do not invent dataset metadata, upload limits, formulas, weights, thresholds or scientific results. Mark proposals as proposals and list open questions.
- Before each PR, report test results and unresolved issues honestly, including checks you could not run.
