"""Earth-vs-Mars comparison pipeline, independent of FastAPI.

validate -> plan common footprint -> harmonize both DEMs -> features ->
Jensen-Shannon similarities -> weighted total -> preview -> contract response.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

import errors
import settings
import similarity
import terrain_features as tf
from preprocessing import HarmonizedGrid, harmonize, near_native, plan_common_grid, preview_grid
from preview import png_data_url
from reference import MarsReference, load_reference
from validation import open_earth_dem

METRICS = ("relative_relief", "slope_distribution", "surface_roughness")


@dataclass(frozen=True)
class FeatureSet:
    histograms: dict[str, tuple[float, ...]]
    samples: dict[str, int]
    max_relief_m: float
    sampling: str = "average"


def compute_features(grid: HarmonizedGrid, label: str) -> FeatureSet:
    z, cell = grid.elevation_m, grid.resolution_m
    arrays = {
        "relative_relief": (tf.local_relief(z, settings.RELIEF_WINDOW_CELLS), settings.RELIEF_BIN_EDGES_M),
        "slope_distribution": (tf.slope_degrees(z, cell), settings.SLOPE_BIN_EDGES_DEG),
        "surface_roughness": (tf.roughness_rms(z, settings.ROUGHNESS_WINDOW_CELLS), settings.ROUGHNESS_BIN_EDGES_M),
    }
    histograms, samples = {}, {}
    for name, (values, edges) in arrays.items():
        fractions, count = tf.histogram_fractions(values, edges)
        if count < settings.MIN_FEATURE_SAMPLES:
            raise errors.fail(
                errors.INSUFFICIENT_VALID_DATA,
                f"Only {count} complete neighbourhoods are available for {name.replace('_', ' ')} "
                f"in the {label} DEM (minimum {settings.MIN_FEATURE_SAMPLES}). Too much data is missing.",
            )
        histograms[name] = tuple(float(v) for v in fractions)
        samples[name] = count
    relief = arrays["relative_relief"][0]
    return FeatureSet(
        histograms=histograms, samples=samples, max_relief_m=float(np.nanmax(relief)), sampling=grid.sampling
    )


@lru_cache(maxsize=32)
def mars_features(reference_id: str, resolution_key: float, cells: int, methodology_version: str) -> FeatureSet:
    """Cached Mars features, keyed by reference, processing scale and methodology version."""
    ref = load_reference(reference_id)
    grid = harmonize(ref.source, resolution_key, cells)
    if grid.valid_fraction < settings.MIN_VALID_FRACTION:
        raise errors.fail(errors.PROCESSING_FAILED, "The Mars reference has insufficient valid data for this footprint.")
    return compute_features(grid, "Mars reference")


def _warning(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def analyze(earth_path: Path, reference_id: str) -> dict:
    ref: MarsReference = load_reference(reference_id)
    earth, facts = open_earth_dem(earth_path)

    resolution, cells = plan_common_grid(earth, ref.source)
    resolution = round(resolution, 6)  # stable cache key; sub-micrometre change
    earth_grid = harmonize(earth, resolution, cells)

    valid_fraction = earth_grid.valid_fraction
    if valid_fraction < settings.MIN_VALID_FRACTION:
        raise errors.fail(
            errors.INSUFFICIENT_VALID_DATA,
            f"Only {valid_fraction:.0%} of the Earth comparison window has valid elevation data "
            f"(minimum {settings.MIN_VALID_FRACTION:.0%}).",
        )

    earth_feat = compute_features(earth_grid, "Earth")
    mars_feat = mars_features(ref.id, resolution, cells, settings.METHODOLOGY_VERSION)

    try:
        scores = {
            m: similarity.distribution_similarity(earth_feat.histograms[m], mars_feat.histograms[m]) for m in METRICS
        }
        total = similarity.total_similarity(scores)
    except similarity.SimilarityError as exc:
        raise errors.fail(errors.PROCESSING_FAILED, "The similarity calculation failed a numerical check.") from exc

    footprint_km = resolution * cells / 1000.0
    warnings = [
        _warning(
            "METHODOLOGY_PROVISIONAL",
            "Scores use a proposed methodology (version "
            f"{settings.METHODOLOGY_VERSION}) that is not yet approved or calibrated. They describe "
            "terrain-geometry similarity only, not habitability or suitability.",
        ),
        _warning(
            "COMPARISON_SCALE",
            f"Compared central {footprint_km:.1f} km x {footprint_km:.1f} km windows of both DEMs at a "
            f"common {resolution:.1f} m resolution ({cells} x {cells} cells).",
        ),
    ]
    if ref.api_object()["effective_resolution_m"] is None:
        warnings.append(
            _warning(
                "EFFECTIVE_RESOLUTION_UNVERIFIED",
                f"The Mars reference grid spacing is about {ref.source.native_spacing_m:.0f} m, but its effective "
                "resolution is not verified. MOLA grid cells are partly interpolated where no laser track was "
                "observed, so real Mars detail may be coarser than the grid. Mars slope and roughness may "
                "therefore be underestimated relative to Earth.",
            )
        )
    for label, src, feat in (("Earth DEM", earth, earth_feat), ("Mars reference", ref.source, mars_feat)):
        if near_native(src, resolution) and feat.sampling != "aligned":
            warnings.append(
                _warning(
                    "NEAR_NATIVE_INTERPOLATED",
                    f"The {label} could not be sampled pixel-for-pixel at the common resolution and was "
                    "area-averaged at a ratio near 1:1, which slightly smooths it.",
                )
            )
    e_sp, m_sp = earth.native_spacing_m, ref.source.native_spacing_m
    if e_sp < m_sp / 1.5:
        warnings.append(
            _warning(
                "RESOLUTION_REDUCED",
                f"The Earth DEM was averaged from about {e_sp:.1f} m to {resolution:.1f} m to match the "
                "Mars reference; finer Earth detail is not used.",
            )
        )
    elif e_sp > m_sp * 1.5:
        warnings.append(
            _warning(
                "EARTH_COARSER_THAN_REFERENCE",
                f"The Earth DEM (about {e_sp:.1f} m) is coarser than the Mars reference ({m_sp:.1f} m); "
                f"both were compared at {resolution:.1f} m.",
            )
        )
    if earth.half_extent_m < ref.source.half_extent_m - resolution:
        warnings.append(
            _warning(
                "FOOTPRINT_LIMITED_BY_EARTH",
                "The Earth DEM is smaller than the Mars reference, so only the central part of the "
                "Mars reference with the same ground size was compared.",
            )
        )
    if valid_fraction < settings.WARN_VALID_FRACTION:
        warnings.append(
            _warning(
                "PARTIAL_COVERAGE",
                f"{1 - valid_fraction:.1%} of the Earth comparison window has no valid elevation data "
                "and was excluded.",
            )
        )
    if facts["vertical_to_metres"] != 1.0:
        warnings.append(_warning("VERTICAL_UNITS_CONVERTED", "Earth elevations were converted from feet to metres."))
    if earth_feat.max_relief_m < settings.FLAT_RELIEF_THRESHOLD_M:
        warnings.append(
            _warning(
                "FLAT_TERRAIN",
                "The Earth window is essentially flat at the comparison resolution, so its terrain "
                "distributions are degenerate.",
            )
        )

    pv = preview_grid(earth, earth_grid.footprint_m)
    response = {
        "status": "success",
        "is_mock": False,
        "reference": ref.api_object(),
        "total_similarity": total,
        "scores": scores,
        "earth_preview_url": png_data_url(pv.elevation_m, pv.valid, pv.resolution_m),
        "charts": {
            "slope_distribution": {
                "unit": "degrees",
                "bin_edges": [float(e) for e in settings.SLOPE_BIN_EDGES_DEG],
                "earth": list(earth_feat.histograms["slope_distribution"]),
                "mars": list(mars_feat.histograms["slope_distribution"]),
            }
        },
        "warnings": warnings,
    }
    _assert_json_safe(response)
    return response


def _assert_json_safe(response: dict) -> None:
    """Refuse to return NaN/Infinity or out-of-range scores."""
    try:
        json.dumps(response, allow_nan=False)
    except ValueError as exc:
        raise errors.fail(errors.PROCESSING_FAILED, "The analysis produced a non-finite value.") from exc
    values = [response["total_similarity"], *response["scores"].values()]
    if not all(isinstance(v, float) and math.isfinite(v) and 0.0 <= v <= 1.0 for v in values):
        raise errors.fail(errors.PROCESSING_FAILED, "The analysis produced an out-of-range score.")
