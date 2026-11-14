# Contributing to Terra Analog

[PROJECT-CONTEXT.md](PROJECT-CONTEXT.md) defines approved scope, stack, data ownership and responsibilities. AI agents also follow [AGENTS.md](AGENTS.md). Proposals elsewhere are not final decisions.

Keep changes focused, avoid unnecessary dependencies and abstractions, and explain important changes.

## Branches

| Branch | Purpose |
| --- | --- |
| `backend--dev` | Backend work (Backend Lead + Claude) |
| `frontend--dev` | Frontend work (Frontend & Data Lead + Codex) |
| `docs/<topic>` | Short-lived documentation changes, created from the latest `origin/main` |
| `main` | Reviewed integration. It must remain runnable once implementation begins. |

## Phase workflow (mandatory)

Every phase follows these steps in order:

1. Develop on the assigned branch.
2. Run local tests.
3. Test frontend/backend integration where applicable.
4. Create a pull request to `main`, reporting test results and unresolved issues.
5. A human reviews and approves the changes.
6. Merge into `main`. Only a human merges.
7. Test the integrated `main` branch.
8. Sync `backend--dev` and `frontend--dev` with `main` by merging `main` into each. Do not rebase or force-push.
9. Start the next phase.

The team defines each phase's scope. Phase 0 is the documentation and architecture revision. No application code is written in Phase 0.

## Rules

- Never merge automatically. AI agents never merge or approve pull requests.
- Never force-push or rewrite shared history.
- Do not work directly on `main`.
- Stage files by explicit path. Do not use `git add .` or `git add -A`.
- Never commit `.venv`, `node_modules`, large DEMs, uploads, generated rasters, secrets or API keys.
- Request the other lead's review for shared interfaces: the API contract, `data/examples/` and reference data.
- Keep unrelated changes in separate pull requests.

## Validation

- **Documentation:** check relative links, JSON examples, terminology, consistency with PROJECT-CONTEXT.md, and the diff for accidental code, secrets or datasets. Run `git diff --check`.
- **Application changes:** run relevant tests and report the results in the PR. Document tests that could not run; do not claim planned checks have passed.

## Recommended GitHub setup

These settings are recommendations and are not verified as configured. An authorized administrator should:

- Verify collaborator access.
- Protect `main` with pull requests and one reviewer.
- Restrict force pushes and branch deletion.
- Avoid requiring CI checks until those checks exist.

Issues with owners and acceptance criteria, labels (documentation/backend/frontend/data/blockers) and a simple board are suggested.
