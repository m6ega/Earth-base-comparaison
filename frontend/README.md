# Frontend

**Status:** no code yet. Implementation starts in Phase 1, once the readiness criteria below are met.

**Owner:** Frontend & Data Lead + Codex, on `frontend--dev`. Scope, stack and responsibilities: [PROJECT-CONTEXT.md](../PROJECT-CONTEXT.md).

The frontend is a React + Vite single-page application. It performs no scientific calculations; it displays what the backend returns.

## Required reading

**Codex must read and follow [docs/ui-concept.md](../docs/ui-concept.md) and [docs/api-contract.md](../docs/api-contract.md) before implementing the frontend.** It must also read [PROJECT-CONTEXT.md](../PROJECT-CONTEXT.md), [AGENTS.md](../AGENTS.md) and [CONTRIBUTING.md](../CONTRIBUTING.md).

- UI behavior must match the approved UI specification. Significant design changes need human approval.
- The API contract is the source of truth for backend/frontend communication. Do not change it without cross-team agreement; report conflicts instead.
- Claude owns backend implementation. Codex owns frontend implementation.

## Intended structure

A recommendation for after Phase 1 begins; do not create unused files. Use JSX or TypeScript consistently, and document the choice before implementation.

```text
frontend/
  package.json
  index.html
  src/
    main.jsx
    App.jsx
    components/    Header, FileUpload, MarsReferenceCard, AnalysisLoading,
                   ComparisonMaps, ZoomableMap, SimilaritySummary,
                   SimilarityChart, SlopeDistributionChart, WarningsPanel,
                   AboutModal, LanguageToggle   (.jsx)
    services/api.js
    i18n/translations.js
    styles/globals.css
    utils/formatters.js
  public/assets/
```

## Folder ownership rules

- All React UI code belongs in `frontend/`.
- API client functions: `frontend/src/services/`.
- Translations: `frontend/src/i18n/`.
- Styling: `frontend/src/styles/`, or another consistent, documented structure.
- Formatting utilities: `frontend/src/utils/`.
- Static frontend-only assets: `frontend/public/assets/`.
- Large Mars DEM rasters and Earth DEM data do **not** belong in `frontend/`.
- Terrain metric calculation code does **not** belong in `frontend/`.
- Do not modify backend-owned files without permission.

## Phase 1 readiness

Codex may begin frontend implementation when:

1. Phase 0 documentation is approved and merged.
2. The UI concept has been reviewed by the Frontend & Data Lead.
3. The API contract is approved by both sides.
4. `frontend--dev` is synchronized with `main`.

Phase 1 initial frontend work:

- Scaffold React + Vite.
- Build the header and upload layout.
- Implement EN/RU localization.
- Connect to `GET /health`.
- Build a basic mock-supported UI for integration testing, labelled with the DEMO / MOCK DATA indicator.

Upload, terrain maps, charts and the full results view belong to later phases. Do not build them early without explicit approval from the human developers. All work follows the [phase workflow](../CONTRIBUTING.md#phase-workflow-mandatory).

## Data research (Frontend & Data Lead + Codex)

Research the NASA MOLA source for Gale Crater and record its provenance in [data/README.md](../data/README.md). Record only verified values.
