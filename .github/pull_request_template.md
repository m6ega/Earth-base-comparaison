## Purpose

Describe the problem, resulting change and related issue.

## Branch

Source branch (`backend--dev`, `frontend--dev` or a `docs/<topic>` branch) and target branch (`main`).

## Scope

List affected areas and distinguish approved decisions from proposals.

## Validation

Describe checks performed and results. For documentation-only changes, report link and consistency checks. Explain unavailable or deferred tests.

## API, methodology and data impact

Describe interface changes, processing assumptions, dataset provenance or attribution changes; write "None" when appropriate.

## Checklist

- [ ] Changes follow PROJECT-CONTEXT.md and remain within the requested scope.
- [ ] No application implementation is introduced before November 14, 2026.
- [ ] `POST /analyze` fields remain `file`, `planet` and `reference_id`, or the change is agreed by both leads.
- [ ] Responses match the approved mock files in `data/examples/`; `total_similarity` and per-metric `scores` stay within 0–1.
- [ ] Similarity uses only the three MVP terrain metrics and is described as geometric terrain similarity, not habitability or base suitability.
- [ ] No aridity, lithology or other deferred feature is added without separate human approval.
- [ ] Documentation and relevant links are updated.
- [ ] No secrets, uploaded DEMs or large generated datasets are included.
- [ ] Files were staged by explicit path, not with `git add .` or `git add -A`.
- [ ] Relevant validation is reported accurately.
- [ ] Shared API, methodology or reference data changes have review from both lead roles.
- [ ] Unresolved decisions and limitations are clearly identified.
- [ ] A human will approve the merge; no automated agent merge.
