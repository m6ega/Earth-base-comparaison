# Frontend preparation

**Status:** documentation only; implementation starts November 14, 2026.

## Confirmed decisions

[Project context](../PROJECT-CONTEXT.md) assigns the Frontend & Data Lead ownership of the user interface, data source research and reference datasets. React is the planned frontend technology.

The interface must support planet selection, reference region selection, Earth DEM upload, results visualization, and error and warning display. Global Earth scanning is outside scope.

## Proposed user flow

1. Select Mars or the Moon and an available reference region.
2. Upload an Earth DEM, with format and size guidance once agreed.
3. Submit analysis and show a clear processing state.
4. Display the agreed terrain comparisons and their limitations.
5. Present actionable errors and preserve warnings alongside results.

Proposal: provide accessible labels, keyboard navigation, clear loading states and textual explanations alongside graphics. Avoid presenting an uncalibrated similarity score as a probability.

## Hackathon checklist and open questions

- Agree on the [API contract](../docs/api-contract.md), including error and warning presentation.
- Select React tooling and package versions; no build system is chosen yet.
- Decide how reference region metadata reaches the interface; no catalog endpoint is confirmed.
- Agree on visualization types, units, score interpretation and sample results.
- Implement and validate the flow beginning November 14.

No application scaffold, dependencies or run commands exist yet. See [architecture](../docs/architecture.md) and [contribution rules](../CONTRIBUTING.md).
