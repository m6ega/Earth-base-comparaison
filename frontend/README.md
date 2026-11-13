# Frontend preparation

**Status:** documentation only; implementation starts November 14, 2026.

## Approved decisions

[Project context](../PROJECT-CONTEXT.md) assigns the Frontend & Data Lead ownership of the user interface, research of NASA planetary reference data, and documentation of its provenance. React is the planned frontend technology. Frontend work happens on `frontend--dev`, with pull requests to `main` approved by humans.

The interface must support planet selection, reference selection, Earth DEM upload, results visualization, and error and warning display. It sends one Earth DEM GeoTIFF to `POST /analyze` as `file`, together with `planet` (`mars` or `moon`) and `reference_id`. Global Earth scanning is outside scope.

Results cover three MVP terrain metrics: relative relief, slope distribution and surface roughness. A successful response always includes `total_similarity` and per-metric `scores`, each from 0 to 1, plus `warnings`; see [analyze-success.json](../data/examples/analyze-success.json) and [analyze-error.json](../data/examples/analyze-error.json). The mock values are illustrative and can be used for UI development before the backend exists.

Scores describe geometric terrain similarity only. The interface must not present them as habitability, base suitability or a probability. Earth aridity and lithology are deferred optional features, not approved for the MVP, and are not shown.

## Proposed user flow

1. Select Mars or the Moon and an available prepared reference.
2. Upload an Earth DEM GeoTIFF, with size guidance once agreed.
3. Submit analysis and show a clear processing state.
4. Display `total_similarity`, the three metric scores and their limitations.
5. Present actionable errors and preserve warnings alongside results.

Proposal: provide accessible labels, keyboard navigation, clear loading states and textual explanations alongside graphics.

## Hackathon checklist and open questions

- Agree on the remaining [API contract](../docs/api-contract.md) details, including error and warning presentation.
- Select React tooling and package versions; no build system is chosen yet.
- Decide how the list of available `reference_id` values reaches the interface; no catalog endpoint is confirmed.
- Agree on visualization types and how 0–1 scores are displayed (for example, decimals or percentages).
- Document provenance for researched NASA reference data in [data/README.md](../data/README.md).
- Implement and validate the flow beginning November 14.

No application scaffold, dependencies or run commands exist yet. See [architecture](../docs/architecture.md) and [contribution rules](../CONTRIBUTING.md).
