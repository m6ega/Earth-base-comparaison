# Terra Analog — Frontend UI Concept

**Status:** Phase 0 concept; no React implementation yet  
**Frontend stack planned by team:** React + Vite  
**Primary user journey:** Upload Earth GeoTIFF → select Mars reference → analyze → inspect comparison results.

## 1. Product and design goals

Terra Analog is a scientific terrain-comparison interface. It should feel like a clean geospatial research tool: restrained, readable, data-first and transparent about limitations.

Design direction:
- Dark navy scientific dashboard, not a game or sci-fi cockpit.
- Cyan/blue accent used sparingly for active controls and data highlights.
- Earth and Mars visualizations receive the most screen space.
- Clear labels, units, scale bars and data provenance.
- No decorative 3D planets, animated starfields or complex animation in the MVP.

## 2. Design system

### Colour palette

| Token | Hex | Use |
|---|---|---|
| `bg` | `#0B1220` | Main page background |
| `surface` | `#111C2E` | Cards and panels |
| `surfaceRaised` | `#17263A` | Inputs, nested panels |
| `border` | `#26384F` | Subtle dividers and outlines |
| `accent` | `#38BDF8` | Primary action, selected state |
| `accentMuted` | `#164E70` | Accent background |
| `text` | `#E8EEF7` | Main text |
| `textMuted` | `#94A3B8` | Secondary text |
| `success` | `#34D399` | Successful state |
| `warning` | `#FBBF24` | Data caveats/warnings |
| `error` | `#F87171` | Validation and request errors |

### Typography

Use a readable sans-serif family such as Inter (or system sans-serif fallback). Use:
- Strong page title and section headings.
- Tabular numerals for scores and measurements.
- Small but readable labels for units and data sources.
- Avoid all-caps body text; reserve uppercase for short map labels or eyebrow headings.

### Layout

- Desktop: centred content, max-width around 1440px, 12-column or CSS grid layout.
- Tablet: stack the main map panels when the viewport becomes too narrow.
- Mobile: single column, Earth and Mars maps stacked, controls full-width, charts stacked.
- Keep navigation and page title consistent across screens.
- Do not force Earth and Mars into a shared map projection or shared basemap.

## 3. Screen 1 — Upload and configuration

### Purpose

Allow a user to choose a valid Earth DEM, select an available Mars reference and start the analysis.

### Desktop wireframe

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ TERRA ANALOG                          Home   Method   Data Sources       │
├─────────────────────────────────────────────────────────────────────────┤
│ TERRAIN ANALYSIS                                                         │
│ Compare an Earth elevation model with a planetary reference.             │
│                                                                         │
│ ┌─────────────────────────────────────┐  ┌────────────────────────────┐ │
│ │  01  EARTH ELEVATION DATA            │  │  02  MARS REFERENCE        │ │
│ │                                     │  │                            │ │
│ │  ┌───────────────────────────────┐  │  │  Planet: Mars               │ │
│ │  │ Drop GeoTIFF here             │  │  │  Region: [ Gale Crater  v ] │ │
│ │  │ or [ Browse files ]           │  │  │                            │ │
│ │  │                               │  │  │  Gale Crater                │ │
│ │  │ .tif / .tiff                  │  │  │  5.44°S, 137.70°E            │ │
│ │  │                               │  │  │  MOLA MEGDR topography      │ │
│ │  └───────────────────────────────┘  │  └────────────────────────────┘ │
│ │  File name · size · validation     │                                 │
│ └─────────────────────────────────────┘                                 │
│                                                                         │
│  Requirements: numeric elevation GeoTIFF; supported size/CRS details   │
│  are checked by the server.                                            │
│                                                                         │
│                    [ Analyze Terrain ]                                  │
│                                                                         │
│  Status / validation message appears here.                             │
└─────────────────────────────────────────────────────────────────────────┘
```

### Components and behavior

| Component | Behavior |
|---|---|
| Logo/title | Returns to upload/home screen |
| File drop zone | Accepts `.tif` and `.tiff`; also opens file picker |
| Browse files | Opens native file selection dialog |
| Selected file row | Shows filename and size after selection |
| Remove file | Clears selected file |
| Reference selector | Loads choices from `GET /references`; Gale is initial required option |
| Reference details | Shows name, coordinates, dataset/resolution metadata supplied by API |
| Analyze Terrain | Disabled until a file is selected and client-side basic checks pass; submits multipart file and reference ID to `POST /analyze` |
| Validation area | Explains unsupported extension, missing file, excessive file size if limit is known, or server validation errors |
| Loading state | Changes button to disabled processing state and shows server status if available |

Do not claim a file is a valid DEM based only on its extension. The backend must validate that the GeoTIFF contains usable numerical elevation data and supported georeferencing.

### Upload requirements and validation copy

Initial client-side checks:
- File extension is `.tif` or `.tiff`.
- File is present.
- File size is within a limit supplied/configured by the backend team.

Backend validation must decide whether the file is actually a readable elevation GeoTIFF, whether it has a usable CRS, whether NoData values are handled and whether its dimensions/resolution are acceptable.

Example messages:
- `Select an Earth elevation GeoTIFF to continue.`
- `Unsupported file type. Upload a .tif or .tiff file.`
- `The file was selected, but its DEM contents have not yet been validated.`
- `This GeoTIFF could not be read. Check the file and try again.`

Do not add “Try Demo” unless a real, licensed/appropriate sample dataset is included and connected to the same analysis pipeline.

## 4. Loading / processing state

Loading is a state of the upload/analysis flow, not necessarily a separate route.

Display:
- `Uploading Earth DEM`
- `Validating raster metadata`
- `Preparing terrain comparison`
- `Calculating terrain metrics`
- `Generating previews and charts`

Only show percentage progress if the backend provides real progress values. Otherwise use an indeterminate progress indicator and truthful status text. Do not fabricate percentages or imply a processing stage has completed when the API has not confirmed it.

Controls:
- `Cancel` only if the backend supports cancellation.
- `Back` should be disabled or confirm navigation while a request is active.
- On success, navigate to Results.
- On failure, show an actionable error and a retry option.

## 5. Screen 2 — Analysis results

### Purpose

Present the Earth and Mars terrain previews side by side, explain the numerical similarity score and show supporting metric comparisons.

### Desktop wireframe

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ TERRA ANALOG                         New Analysis   Method   Data Sources   │
├────────────────────────────────────────────────────────────────────────────┤
│ RESULTS  /  EARTH ↔ MARS TERRAIN COMPARISON                                 │
│ Earth DEM: [uploaded filename]        Reference: Gale Crater, Mars          │
│                                                                            │
│ ┌──────────────────────────────┐       ┌──────────────────────────────┐    │
│ │ EARTH — UPLOADED DEM         │       │ MARS — GALE CRATER           │    │
│ │                              │       │                              │    │
│ │ [Earth preview PNG]          │       │ [Mars preview PNG]           │    │
│ │                              │       │                              │    │
│ │ scale bar · units · extent   │       │ scale bar · units · extent   │    │
│ │ [layer selector]             │       │ [layer selector]             │    │
│ └──────────────────────────────┘       └──────────────────────────────┘    │
│                                                                            │
│ ┌────────────────────────────────────────────────────────────────────────┐ │
│ │ OVERALL TERRAIN SIMILARITY                                               │ │
│ │                         00.0 / 100                                      │ │
│ │ Score definition and comparison-method note                             │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│ ┌───────────────────┐ ┌───────────────────┐ ┌────────────────────────────┐ │
│ │ Relative relief   │ │ Slope distribution│ │ Surface roughness         │ │
│ │ score             │ │ score              │ │ score                     │ │
│ └───────────────────┘ └───────────────────┘ └────────────────────────────┘ │
│                                                                            │
│ ┌────────────────────────────────────┐ ┌────────────────────────────────┐ │
│ │ Metric comparison chart            │ │ Interpretation                 │ │
│ │ Earth vs Mars profile/distribution │ │ Similarities and differences   │ │
│ └────────────────────────────────────┘ └────────────────────────────────┘ │
│                                                                            │
│ Data sources · preprocessing · CRS/resolution · warnings · limitations     │
│ [ Analyze Another Region ]                                                  │
└────────────────────────────────────────────────────────────────────────────┘
```

### Main results layout decisions

1. Earth and Mars preview panels are equal visual size and placed side by side on desktop.
2. Each preview is a separate image with its own planet-specific coordinate context.
3. Each preview must include a scale bar or scale information supplied by the backend. If scale information is unavailable, show `Scale unavailable` rather than inventing it.
4. Do not imply that the two images cover equal ground areas unless their extents and dimensions have been reconciled by the backend.
5. The overall score is prominent, but the metric breakdown and method note remain visible.
6. Use a small interpretation panel to explain what the metrics indicate without making claims about habitability or geological identity.

### Metric cards and chart choices

| Metric | UI presentation | Backend data needed |
|---|---|---|
| Overall terrain similarity | Large score, 0–100 only if agreed | `total_similarity`, score scale/method |
| Relative relief | Score card plus Earth/Mars relief values | `relative_relief.score`, Earth and Mars values, units |
| Slope distribution | Score card plus overlaid histogram or paired distribution chart | Bins and Earth/Mars frequencies or comparable summary data |
| Surface roughness | Score card plus paired distribution/bar comparison | Method/window scale, Earth and Mars values, units |

For the first MVP chart, use a grouped bar chart for the three metric scores or a paired histogram for slope distribution if the backend returns bins. Avoid inventing chart values in the frontend.

Terrain preview layer options can include elevation, hillshade, slope and roughness only when the backend supplies corresponding preview images. The frontend does not calculate these layers.

### Results actions

| Control | Behavior |
|---|---|
| Analyze Another Region | Returns to upload/configuration and clears prior result state |
| Layer selector | Switches the displayed preview among available backend-generated layers |
| Download report | Optional; only show if report generation is implemented |
| Data source link | Opens the cited dataset/source in a new browser context |

No unsupported map actions should be shown. Pan/zoom controls are only included if the preview/map component actually supports them.

## 6. Warnings and limitations

Show a persistent but compact `Data & Method` section with:
- Earth DEM source and CRS.
- Mars reference dataset and tile/product identifier.
- Effective resolution and comparison area for each raster.
- Resampling or preprocessing applied.
- Metric definitions and roughness scale/window.
- NoData handling.
- Known limitations.

Warning examples:
- `The input CRS or elevation units could not be confirmed.`
- `Earth and Mars elevations use different reference surfaces; absolute elevations are not directly compared.`
- `The two preview extents are not confirmed to represent equal ground areas.`
- `Aridity/lithology data are unavailable for this run.`

Do not display environmental comparisons or lithology scores unless compatible, documented data and a scientifically defensible comparison method are available.

## 7. Error states

| Situation | Message | Action |
|---|---|---|
| No file selected | Select an Earth DEM before analysis. | Browse files |
| Wrong extension | Upload a `.tif` or `.tiff` file. | Choose another file |
| Invalid/corrupt raster | The server could not read this GeoTIFF. | Try another file |
| Missing/unsupported CRS | Spatial reference could not be confirmed. | Review file / contact team |
| File too large | File exceeds the current upload limit. | Choose smaller file |
| API unavailable | Terra Analog could not connect to the analysis service. | Retry |
| Analysis failed | Analysis did not complete. No score is available. | Try again |
| Missing preview | Numerical results are available, but this preview could not be loaded. | Retry preview |
| Missing metric | This metric was not calculated for this run. | Show `Not available` |

Never show a made-up score when analysis fails or a metric is absent.

## 8. Frontend component list

Suggested React components (for implementation after Phase 0 approval):
- `AppShell`
- `TopNavigation`
- `UploadPage`
- `GeoTiffDropzone`
- `SelectedFileSummary`
- `ReferenceSelector`
- `AnalysisProgress`
- `ResultsPage`
- `PlanetPreviewPanel`
- `LayerSelector`
- `SimilarityScoreCard`
- `MetricScoreCard`
- `MetricComparisonChart`
- `InterpretationPanel`
- `DataLimitationsPanel`
- `ErrorNotice`

## 9. Proposed API data requirements

These are frontend requirements to discuss with the backend developer. They are **not a finalized contract**.

### `GET /health`

Expected minimum:
```json
{
  "status": "ok"
}
```

### `GET /references`

Expected minimum:
```json
{
  "references": [
    {
      "id": "mars_gale_mola_128ppd",
      "name": "Gale Crater",
      "planet": "Mars",
      "latitude": -5.44,
      "longitude_east": 137.70,
      "dataset": "MGS MOLA MEGDR topography",
      "resolution": {
        "value": 128,
        "unit": "pixels_per_degree"
      },
      "available": true
    }
  ]
}
```

### `POST /analyze`

Request:
- `multipart/form-data`
- `earth_dem`: uploaded `.tif`/`.tiff`
- `reference_id`: selected reference identifier

Proposed response:
```json
{
  "analysis_id": "example-analysis-id",
  "status": "completed",
  "reference": {
    "id": "mars_gale_mola_128ppd",
    "name": "Gale Crater",
    "planet": "Mars"
  },
  "earth": {
    "filename": "uploaded-dem.tif",
    "preview_url": "/results/example/earth-preview.png",
    "crs": "backend-reported CRS",
    "horizontal_units": "backend-reported units",
    "elevation_units": "backend-reported units",
    "resolution": "backend-reported resolution",
    "extent": "backend-reported extent",
    "scale_bar": "backend-provided scale information"
  },
  "mars": {
    "preview_url": "/results/example/mars-preview.png",
    "dataset": "MGS MOLA MEGDR topography",
    "product_id": "megt00n090hb",
    "crs": "backend-reported Mars spatial reference",
    "elevation_units": "backend-reported units",
    "resolution": "backend-reported resolution",
    "extent": "backend-reported extent",
    "scale_bar": "backend-provided scale information"
  },
  "scores": {
    "total_similarity": null,
    "score_scale": "0-100",
    "relative_relief": {
      "score": null,
      "earth_value": null,
      "mars_value": null,
      "unit": null
    },
    "slope_distribution": {
      "score": null,
      "earth_summary": {},
      "mars_summary": {},
      "chart": {
        "bins": [],
        "earth": [],
        "mars": []
      }
    },
    "surface_roughness": {
      "score": null,
      "earth_value": null,
      "mars_value": null,
      "method": null,
      "window_scale": null,
      "unit": null
    }
  },
  "interpretation": [],
  "warnings": [],
  "limitations": [],
  "provenance": {
    "earth_source": null,
    "mars_source_url": "https://pds-geosciences.wustl.edu/missions/mgs/megdr.html",
    "processing_version": null
  }
}
```

All `null` and empty values above are placeholders for schema illustration, not real analysis results. The backend team must finalize field names, types, units, score semantics, URL behavior and error response shape.

### API questions to settle together

1. Does `POST /analyze` return results synchronously, or return an `analysis_id` for polling?
2. What is the maximum upload size?
3. What CRS and elevation unit requirements are enforced?
4. How are preview URLs served, and for how long?
5. Does the backend provide real progress updates?
6. What is the agreed definition and weighting of each similarity score?
7. What exactly does `relative_relief` mean in this implementation?
8. What roughness algorithm and neighborhood/window size are used?
9. Which chart series/bins are returned?
10. What error JSON schema is used?

## 10. MVP scope

### Required for first working demo
- Upload one Earth GeoTIFF.
- Select Gale Crater as the Mars reference.
- Show Earth and Mars terrain previews independently.
- Show a genuine overall similarity score returned by backend.
- Show relative relief, slope distribution and surface roughness scores when calculated.
- Show at least one genuine chart from backend data.
- Show interpretation, source metadata and limitations.
- Handle invalid upload and failed analysis states.

### Optional after the MVP works
- Gusev Crater.
- Additional layer previews (hillshade, slope, roughness).
- Exportable report.
- Aridity and lithology, only if suitable data and methods are ready.

## 11. Handover checklist

- [ ] Confirm Gale MOLA tile metadata and local conversion with backend developer.
- [ ] Agree API contract and score semantics.
- [ ] Confirm Earth upload size/CRS/elevation-unit requirements.
- [ ] Confirm preview image dimensions, scale-bar metadata and URLs.
- [ ] Review wireframes with teammate before implementation.
- [ ] Keep React implementation out of Phase 0.
