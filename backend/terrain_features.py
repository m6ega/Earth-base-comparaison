"""Pure terrain mathematics on a harmonized square-cell grid.

All functions take elevations in metres (NaN = invalid) and a cell size in
metres, and return arrays of the same shape with NaN wherever the required
neighbourhood is incomplete. A neighbourhood is used only if every cell in it
is valid, so NoData never leaks into a feature value. Nothing here depends on
FastAPI or on file formats.
"""

from __future__ import annotations

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


def _windows(z: np.ndarray, size: int) -> np.ndarray:
    if size < 3 or size % 2 == 0:
        raise ValueError("window size must be an odd integer >= 3")
    pad = size // 2
    padded = np.pad(np.asarray(z, dtype=np.float64), pad, mode="constant", constant_values=np.nan)
    return sliding_window_view(padded, (size, size))


def _complete(win: np.ndarray) -> np.ndarray:
    return np.all(np.isfinite(win), axis=(-2, -1))


def slope_degrees(z: np.ndarray, cell_size_m: float) -> np.ndarray:
    """Slope angle in degrees with Horn's (1981) 3 x 3 finite-difference method.

    dz/dx = ((c + 2f + i) - (a + 2d + g)) / (8 * cell)
    dz/dy = ((g + 2h + i) - (a + 2b + c)) / (8 * cell)
    slope = degrees(arctan(sqrt(dz/dx^2 + dz/dy^2)))
    with the window laid out as
        a b c
        d e f
        g h i
    """
    if not (cell_size_m > 0 and np.isfinite(cell_size_m)):
        raise ValueError("cell size must be positive and finite")
    w = _windows(z, 3)
    ok = _complete(w)
    with np.errstate(invalid="ignore"):
        dzdx = ((w[..., 0, 2] + 2 * w[..., 1, 2] + w[..., 2, 2]) - (w[..., 0, 0] + 2 * w[..., 1, 0] + w[..., 2, 0])) / (
            8.0 * cell_size_m
        )
        dzdy = ((w[..., 2, 0] + 2 * w[..., 2, 1] + w[..., 2, 2]) - (w[..., 0, 0] + 2 * w[..., 0, 1] + w[..., 0, 2])) / (
            8.0 * cell_size_m
        )
        slope = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    return np.where(ok, slope, np.nan)


def local_relief(z: np.ndarray, window: int) -> np.ndarray:
    """Local relative relief: max - min elevation in a (window x window) neighbourhood, metres.

    Independent of the absolute vertical datum and of constant offsets, while
    keeping the physical height difference in metres.
    """
    w = _windows(z, window)
    ok = _complete(w)
    with np.errstate(invalid="ignore"):
        relief = w.max(axis=(-2, -1)) - w.min(axis=(-2, -1))
    return np.where(ok, relief, np.nan)


def roughness_rms(z: np.ndarray, window: int) -> np.ndarray:
    """Surface roughness: RMS of elevation residuals after removing a local plane, metres.

    For each complete (window x window) neighbourhood a plane z = a + b*x + c*y is
    fitted by least squares on cell offsets x, y in {-k..k}; because the offsets
    are symmetric the solution is a = mean(z), b = sum(x z)/sum(x^2),
    c = sum(y z)/sum(y^2). Roughness = sqrt(mean((z - plane)^2)).

    A plane of any slope has zero roughness, so roughness is not a disguised
    slope measure. The window is defined in harmonized cells, so it spans the
    same ground distance for Earth and Mars.
    """
    w = _windows(z, window)
    ok = _complete(w)
    k = window // 2
    offs = np.arange(-k, k + 1, dtype=np.float64)
    x = np.broadcast_to(offs[None, :], (window, window))
    y = np.broadcast_to(offs[:, None], (window, window))
    sxx = float(np.sum(x * x))
    with np.errstate(invalid="ignore"):
        a = w.mean(axis=(-2, -1))
        b = np.sum(w * x, axis=(-2, -1)) / sxx
        c = np.sum(w * y, axis=(-2, -1)) / sxx
        resid = w - (a[..., None, None] + b[..., None, None] * x + c[..., None, None] * y)
        rms = np.sqrt(np.mean(resid * resid, axis=(-2, -1)))
    return np.where(ok, rms, np.nan)


def histogram_fractions(values: np.ndarray, bin_edges: list[float]) -> tuple[np.ndarray, int]:
    """Fractions of finite values per bin with fixed, shared edges.

    Values below the first edge or above the last edge are counted in the first
    or last bin respectively (the last bin is open-ended in practice).
    Returns (fractions, number_of_values). Fractions are all zero if no values.
    """
    edges = np.asarray(bin_edges, dtype=np.float64)
    if edges.ndim != 1 or edges.size < 2 or np.any(np.diff(edges) <= 0):
        raise ValueError("bin edges must be strictly increasing")
    v = np.asarray(values, dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return np.zeros(edges.size - 1), 0
    clipped = np.clip(v, edges[0], edges[-1])
    counts, _ = np.histogram(clipped, bins=edges)
    return counts / counts.sum(), int(v.size)
