"""Distribution similarity and score aggregation (pure functions)."""

from __future__ import annotations

import math

import numpy as np
from scipy.spatial.distance import jensenshannon

import settings


class SimilarityError(ValueError):
    """A distribution or score failed a numerical sanity check."""


def _as_distribution(p) -> np.ndarray:
    arr = np.asarray(p, dtype=np.float64)
    if arr.ndim != 1 or arr.size == 0:
        raise SimilarityError("distribution must be a non-empty 1-D array")
    if not np.all(np.isfinite(arr)) or np.any(arr < 0):
        raise SimilarityError("distribution must be finite and non-negative")
    total = arr.sum()
    if not total > 0:
        raise SimilarityError("distribution must have positive mass")
    return arr / total


def js_distance(p, q, base: float = settings.JS_LOG_BASE) -> float:
    """Jensen-Shannon distance (square root of JS divergence).

    With base 2 the distance lies in [0, 1]: 0 for identical distributions and 1
    for distributions with disjoint support. Zero bins are handled by the
    0 * log(0) = 0 convention inside SciPy.
    """
    pn, qn = _as_distribution(p), _as_distribution(q)
    if pn.shape != qn.shape:
        raise SimilarityError("distributions must use identical bins")
    d = float(jensenshannon(pn, qn, base=base))
    if not math.isfinite(d):
        raise SimilarityError("Jensen-Shannon distance is not finite")
    upper = 1.0 if base == 2.0 else math.sqrt(math.log(2.0, base))
    if d < -1e-12 or d > upper + 1e-9:
        raise SimilarityError(f"Jensen-Shannon distance {d} is outside [0, {upper}]")
    return min(max(d, 0.0), upper)


def score_from_distance(distance: float) -> float:
    """Contract score in [0, 1]: 1 - JS distance (base 2)."""
    s = 1.0 - distance
    if not (math.isfinite(s) and 0.0 <= s <= 1.0):
        raise SimilarityError(f"score {s} is outside [0, 1]")
    return s


def distribution_similarity(p, q) -> float:
    return score_from_distance(js_distance(p, q))


def total_similarity(scores: dict[str, float], weights: dict[str, float] = settings.SCORE_WEIGHTS) -> float:
    """Weighted mean of the per-metric scores (weights are a proposal)."""
    if set(scores) != set(weights):
        raise SimilarityError("scores and weights must cover the same metrics")
    wsum = sum(weights.values())
    if not wsum > 0:
        raise SimilarityError("weights must sum to a positive value")
    total = sum(weights[k] * scores[k] for k in weights) / wsum
    if not (math.isfinite(total) and -1e-12 <= total <= 1.0 + 1e-12):
        raise SimilarityError(f"total similarity {total} is outside [0, 1]")
    return min(max(total, 0.0), 1.0)
