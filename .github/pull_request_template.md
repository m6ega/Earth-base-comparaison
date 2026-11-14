## Purpose

Describe the problem, the resulting change and the related issue.

## Branch and phase

Source branch (`backend--dev`, `frontend--dev` or `docs/<topic>`), target branch (`main`) and phase.

## Scope

List affected areas. Distinguish approved decisions from proposals.

## Validation

Report local test results, frontend/backend integration results where applicable, and checks that could not run. For documentation-only changes, report link, JSON and consistency checks and `git diff --check`.

## Unresolved issues

List known problems and open decisions, or write "None".

## API, methodology and data impact

Describe interface changes, processing assumptions, and dataset provenance or attribution changes, or write "None".

## Checklist

- [ ] Changes follow PROJECT-CONTEXT.md and stay within the requested scope and ownership area.
- [ ] Responses match `docs/api-contract.md`. Fixtures in `data/examples/` keep `is_mock: true`, and mock values are not presented as results.
- [ ] Similarity is described as geometric terrain similarity only, not habitability or base suitability.
- [ ] No deferred feature (Moon, morphology, aridity, lithology) is added without separate human approval.
- [ ] No `.venv`, `node_modules`, large DEMs, uploads, generated rasters or secrets are included.
- [ ] Files were staged by explicit path.
- [ ] Shared API, fixture or reference data changes have review from both leads.
- [ ] After merge: integrated `main` will be tested, and `backend--dev` and `frontend--dev` synced.
- [ ] A human will approve the merge; no automated agent merge.
