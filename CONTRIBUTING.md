# Contributing to Terra Analog

## Authority and preparation boundary

[PROJECT-CONTEXT.md](PROJECT-CONTEXT.md) defines approved scope, architecture and team responsibilities. AI agents must also follow [AGENTS.md](AGENTS.md). Technical proposals elsewhere are not final decisions.

Until November 14, 2026, work is limited to planning, documentation and repository preparation. Do not implement or scaffold the application, install project dependencies, or imply that proposed behavior already exists. The hackathon is planned for November 14–15, 2026.

Keep changes focused, avoid unnecessary dependencies and abstractions, explain important changes, and never commit secrets or API keys.

## Ownership

| Area | Approved owner role |
| --- | --- |
| Backend, terrain processing, similarity algorithm and API | Backend Lead |
| Validation, preparation, storage and integration of planetary reference data | Backend Lead |
| Frontend and user interface | Frontend & Data Lead |
| Research of NASA planetary reference data and provenance documentation | Frontend & Data Lead |

Proposal: both leads review API, methodology and shared data assumptions. Assign actual people in GitHub; this document does not grant permissions.

## Branch workflow (approved)

| Branch | Purpose |
| --- | --- |
| `backend--dev` | Backend work |
| `frontend--dev` | Frontend work |
| `main` | Reviewed integration |

- Pull requests target `main`.
- Humans approve pull requests and merges. AI agents never merge automatically.
- Do not work directly on `main`.
- Documentation changes may use a short-lived `docs/<topic>` branch created from the latest `origin/main`.
- Do not force-push shared history.
- Stage files by explicit path; do not use `git add .` or `git add -A`.
- Describe purpose, affected areas and validation in each PR. Request the other lead's review for shared interfaces such as the API contract and reference data. Keep unrelated changes separate.

Open: `backend--dev` and `frontend--dev` were created before the project documentation reached `main`. A human should bring them up to date with `main` (for example, by merging `main` into them) before development starts.

## Validation

For documentation, check relative links, terminology, consistency with project context, and the final diff for accidental code, secrets or datasets. For application changes beginning November 14, run relevant tests and report results before committing. Document unavailable tests honestly; do not claim planned checks have passed.

## Proposed GitHub collaboration setup

An authorized repository administrator should verify collaborator access, assign owners, and configure PR-based protection for `main` with one reviewer where supported. Restrict force pushes and branch deletion. Do not require CI checks before those checks exist.

Use issues with an owner and acceptance criteria, labels for documentation/backend/frontend/data/blockers, a November 14–15 milestone, and a Todo / In progress / Review / Done board. These settings are recommendations and have not been verified or configured by this documentation change.

## Readiness checklist

- [ ] Team has reviewed the preparation documents and their open questions.
- [ ] `backend--dev` and `frontend--dev` are up to date with `main`.
- [ ] Collaborator permissions are verified.
- [ ] Branch protection for `main` is configured.
- [ ] Both leads agree on the remaining API details (limits, response and error schema).
- [ ] Metric definitions, units, normalization and score interpretation are agreed for the three MVP metrics.
- [ ] Planetary reference data has documented provenance, usage terms and resolution.
- [ ] Tasks have owners and acceptance criteria for November 14–15.
- [ ] Documentation links and ignore rules are checked.
- [ ] No application implementation was introduced before November 14.
