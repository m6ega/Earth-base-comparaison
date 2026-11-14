"""Central configuration for the Terra Analog backend.

Every numeric threshold, bin edge and weight below is a PROPOSAL recorded in
backend/README.md ("Scientific method"). None of them is approved in
docs/methodology.md yet. Change them here only, and bump METHODOLOGY_VERSION
whenever a value that affects scores changes (this invalidates cached Mars
features automatically, because the cache key includes the version).
"""

from __future__ import annotations

import os
from pathlib import Path

METHODOLOGY_VERSION = "0.2-proposal"  # 0.2: pixel-aligned sampling of near-native DEMs

BACKEND_DIR = Path(__file__).resolve().parent
REFERENCES_DIR = BACKEND_DIR / "references"

# --- Upload and memory limits -------------------------------------------------
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # approved: 50 MB file limit
# Multipart framing adds a few hundred bytes; 1 MiB of headroom is generous.
MAX_REQUEST_BODY_BYTES = MAX_UPLOAD_BYTES + 1024 * 1024
MAX_RASTER_PIXELS = 200_000_000  # header-declared width * height
MAX_READ_WINDOW_PIXELS = 40_000_000  # pixels actually decoded into memory
MIN_RASTER_SIDE_PIXELS = 3
UPLOAD_CHUNK_BYTES = 1024 * 1024
ALLOWED_EXTENSIONS = (".tif", ".tiff")
ALLOWED_DTYPES = {
    "int8", "uint8", "int16", "uint16", "int32", "uint32", "float32", "float64",
}

# --- Physical-scale harmonization --------------------------------------------
# A harmonized grid narrower than this many cells is too poorly resolved for
# distribution statistics, so the request is rejected.
MIN_GRID_CELLS = 32
# A harmonized cell is valid only if at least this fraction of its area is
# covered by valid source pixels.
MIN_CELL_COVERAGE = 0.5
# A DEM whose ground spacing differs from the common cell size by at most this
# fraction on both axes is sampled pixel-for-pixel on its own lattice instead of
# being area-averaged (which at ~1:1 would blur it). The accepted scale error is
# this fraction; Gale is 0.45 % east-west (460.97 m spacing in 463.06 m cells).
ALIGNED_MAX_SCALE_ERROR = 0.01
# Plausible elevation ranges in metres, used to catch wrong vertical units or
# undeclared NoData sentinels (for example -32768).
ELEVATION_RANGE_M = {
    "earth": (-12_000.0, 9_000.0),
    "mars": (-9_000.0, 22_000.0),
}
# Semi-major axis range used to recognise an Earth ellipsoid (metres).
EARTH_SEMI_MAJOR_RANGE_M = (6_350_000.0, 6_400_000.0)
# Physical pixel spacing sanity range (metres).
PIXEL_SPACING_RANGE_M = (0.1, 50_000.0)

# --- NoData policy ------------------------------------------------------------
MIN_VALID_FRACTION = 0.50  # below this the Earth window is rejected
WARN_VALID_FRACTION = 0.95  # below this a PARTIAL_COVERAGE warning is added
MIN_FEATURE_SAMPLES = 256  # minimum valid neighbourhoods per feature

# --- Feature definitions (cells of the harmonized grid) ----------------------
RELIEF_WINDOW_CELLS = 5  # local relief = max - min in a 5 x 5 window
ROUGHNESS_WINDOW_CELLS = 3  # RMS residual from a plane fitted to 3 x 3 cells
FLAT_RELIEF_THRESHOLD_M = 1.0

# Shared histogram bin edges. Identical edges are used for Earth and Mars.
# Values beyond the last edge are counted in the last bin.
SLOPE_BIN_EDGES_DEG = [0.0, 1.0, 2.0, 3.0, 5.0, 7.5, 10.0, 15.0, 20.0, 30.0, 45.0, 90.0]
RELIEF_BIN_EDGES_M = [0.0, 5.0, 10.0, 20.0, 40.0, 80.0, 160.0, 320.0, 640.0, 1280.0, 2560.0, 10000.0]
ROUGHNESS_BIN_EDGES_M = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0, 10000.0]

# --- Similarity --------------------------------------------------------------
JS_LOG_BASE = 2.0  # base-2 Jensen-Shannon distance lies in [0, 1]
SCORE_WEIGHTS = {  # proposal: equal weights, no scientific claim
    "relative_relief": 1.0 / 3.0,
    "slope_distribution": 1.0 / 3.0,
    "surface_roughness": 1.0 / 3.0,
}

# --- Preview -----------------------------------------------------------------
PREVIEW_MAX_PIXELS_PER_SIDE = 512


def cors_origins() -> list[str]:
    """Local React/Vite and static-server origins; override with TERRA_CORS_ORIGINS."""
    raw = os.environ.get("TERRA_CORS_ORIGINS")
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip() and o.strip() != "*"]
    return [
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
        "http://localhost:4173",  # Vite preview
        "http://127.0.0.1:4173",
        "http://localhost:5500",  # VS Code Live Server (current static frontend)
        "http://127.0.0.1:5500",
    ]
