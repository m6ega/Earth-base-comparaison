# Contributing to Terra Analog

## Authority and preparation boundary

[PROJECT-CONTEXT.md](PROJECT-CONTEXT.md) defines confirmed scope, architecture and team responsibilities. These instructions document the approved preparation workflow; technical proposals elsewhere are not final decisions.

Until November 14, 2026, work is limited to planning, documentation and repository preparation. Do not implement or scaffold the application, install project dependencies, or imply that proposed behavior already exists. The hackathon is planned for November 14–15, 2026.

Keep changes focused, avoid unnecessary dependencies and abstractions, explain important changes, and never commit secrets or API keys. Obtain approval before modifying existing files during repository preparation. Commits, pushes and PR creation for this setup remain pending owner review.

## Ownership

| Area | Confirmed owner role |
| --- | --- |
| Backend, terrain processing, similarity algorithm and API | Backend Lead |
| Frontend, user interface, data source research and reference datasets | Frontend & Data Lead |

Proposal: both leads review API, methodology and shared data assumptions. Assign actual people in GitHub; this document does not grant permissions.

## Branch workflow

- Use `docs/repository-setup` for this documentation preparation, based on local `main`.
- Do not work directly on `main`.
- Existing remote-tracking branches are named `backend--dev` and `frontend--dev`; preserve their names and history.
- Proposal for development: use short-lived `backend/<topic>`, `frontend/<topic>`, `data/<topic>` or `docs/<topic>` branches and reviewed PRs into `main`. If the team uses the existing development branches instead, agree on integration ownership first.
- Before development, verify the live remote and reconcile the development branches with the project context on `main`. Do not force-push shared history.
- Describe purpose, affected areas and validation in each PR. Request the other lead's review for shared interfaces. Keep unrelated changes separate.

## Validation

For documentation, check relative links, terminology, consistency with project context, and the final diff for accidental code, secrets or datasets. For application changes beginning November 14, run relevant tests and report results before committing. Document unavailable tests honestly; do not claim planned checks have passed.

## Proposed GitHub collaboration setup

An authorized repository administrator should verify collaborator access, assign owners, and configure PR-based protection for `main` with one reviewer where supported. Restrict force pushes and branch deletion. Do not require CI checks before those checks exist.

Use issues with an owner and acceptance criteria, labels for documentation/backend/frontend/data/blockers, a November 14–15 milestone, and a Todo / In progress / Review / Done board. These settings are recommendations and have not been verified or configured by this documentation change.

## Readiness checklist

- [ ] Team has reviewed the preparation documents and their open questions.
- [ ] Live remote branches and collaborator permissions are verified.
- [ ] Branch protection and review workflow are agreed and configured.
- [ ] Both leads agree on the API request, response and error contract.
- [ ] Metric definitions, units, normalization and score interpretation are agreed.
- [ ] Reference datasets have provenance, usage terms and comparable resolution.
- [ ] Tasks have owners and acceptance criteria for November 14–15.
- [ ] Documentation links and ignore rules are checked.
- [ ] No application implementation was introduced before November 14.
- [ ] Repository owner has reviewed the setup diff before any commit or push.
