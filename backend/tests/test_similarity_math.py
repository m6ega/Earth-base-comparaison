"""Independent checks of the similarity mathematics.

The Jensen-Shannon reference here is written from the definition, without SciPy:
    M = (P + Q) / 2
    JSD_b(P, Q) = 1/2 * sum_i P_i log_b(P_i / M_i) + 1/2 * sum_i Q_i log_b(Q_i / M_i)   (0 log 0 = 0)
    distance = sqrt(JSD_b),   score = 1 - distance (base 2),   total = mean of the three scores.
Terrain checks use surfaces whose slope, relief and roughness are known in closed form.
"""

import math

import numpy as np
import pytest

import settings
import similarity as sim
import terrain_features as tf
from analysis import METRICS, compute_features
from preprocessing import HarmonizedGrid

CELL = 463.0


def jsd_reference(p, q, base=2.0):
    p = np.asarray(p, float) / np.sum(p)
    q = np.asarray(q, float) / np.sum(q)
    m = (p + q) / 2
    kl = lambda a: sum(ai * math.log(ai / mi, base) for ai, mi in zip(a, m) if ai > 0)  # noqa: E731
    return 0.5 * kl(p) + 0.5 * kl(q)


# --- Known probability distributions ---------------------------------------------------------


@pytest.mark.parametrize(
    "p,q,expected_distance",
    [
        ([1, 0], [1, 0], 0.0),
        ([1, 0], [0, 1], 1.0),  # disjoint support: JSD = 1 bit
        ([0.5, 0.5, 0, 0], [0, 0, 0.5, 0.5], 1.0),
        # JSD = H(M) - (H(P) + H(Q)) / 2 with M = [3/4, 1/4], H(P) = 0, H(Q) = 1 bit
        ([1, 0], [0.5, 0.5], math.sqrt(-(0.75 * math.log2(0.75) + 0.25 * math.log2(0.25)) - 0.5)),
        # M = [1/2, 1/4, 1/4]: H(M) = 1.5 bits, H(P) = H(Q) = 1 bit -> JSD = 0.5
        ([0.5, 0.5, 0], [0.5, 0, 0.5], math.sqrt(0.5)),
    ],
)
def test_js_distance_matches_closed_form(p, q, expected_distance):
    assert sim.js_distance(p, q) == pytest.approx(expected_distance, abs=1e-12)
    assert sim.distribution_similarity(p, q) == pytest.approx(1.0 - expected_distance, abs=1e-12)


def test_js_distance_matches_independent_implementation_and_is_a_metric():
    rng = np.random.default_rng(3)
    for _ in range(300):
        p, q, r = (rng.random(11) ** 3 * (rng.random(11) > 0.3) for _ in range(3))  # with empty bins
        if min(p.sum(), q.sum(), r.sum()) == 0:
            continue
        d_pq = sim.js_distance(p, q)
        assert d_pq == pytest.approx(math.sqrt(max(jsd_reference(p, q), 0.0)), abs=1e-9)
        assert d_pq == pytest.approx(sim.js_distance(q, p), abs=1e-12)  # symmetric
        assert 0.0 <= d_pq <= 1.0
        # The JS *distance* (not the divergence) satisfies the triangle inequality.
        assert d_pq <= sim.js_distance(p, r) + sim.js_distance(r, q) + 1e-12


def test_log_base_only_rescales_the_distance():
    p, q = [0.7, 0.2, 0.1, 0.0], [0.1, 0.3, 0.3, 0.3]
    # JSD_e = JSD_2 * ln 2, so distance_e = distance_2 * sqrt(ln 2); base 2 bounds the distance by 1.
    assert sim.js_distance(p, q, base=math.e) == pytest.approx(sim.js_distance(p, q) * math.sqrt(math.log(2)), rel=1e-12)
    assert settings.JS_LOG_BASE == 2.0


def test_zero_probability_bins_do_not_produce_nan_or_infinity():
    p = [0.0, 0.0, 1.0, 0.0]
    q = [0.25, 0.25, 0.25, 0.25]
    d = sim.js_distance(p, q)
    assert math.isfinite(d)
    assert d == pytest.approx(math.sqrt(jsd_reference(p, q)), abs=1e-12)


def test_normalization_is_scale_invariant():
    p, q = np.array([3.0, 1.0, 0.0, 6.0]), np.array([1.0, 1.0, 1.0, 1.0])
    assert sim.js_distance(p, q) == pytest.approx(sim.js_distance(p / 10, q * 1000), abs=1e-12)


def test_total_is_the_unweighted_mean_with_equal_weights():
    assert set(settings.SCORE_WEIGHTS) == set(METRICS)
    assert all(w == pytest.approx(1 / 3, abs=1e-15) for w in settings.SCORE_WEIGHTS.values())
    rng = np.random.default_rng(5)
    for _ in range(100):
        s = dict(zip(METRICS, rng.random(3)))
        assert sim.total_similarity(s) == pytest.approx(sum(s.values()) / 3, abs=1e-15)


# --- Analytically known terrain ------------------------------------------------------------------


def sine_columns(n, amplitude, wavelength_cells, cell=CELL):
    """z = A sin(k x), constant along y; x = column * cell."""
    x = np.arange(n, dtype=float)[None, :] * cell
    k = 2 * math.pi / (wavelength_cells * cell)
    return np.repeat(amplitude * np.sin(k * x), n, axis=0), x[0], k


def test_horn_slope_of_sinusoid_matches_closed_form():
    # Horn on a y-constant surface reduces to (f(x+c) - f(x-c)) / 2c = A cos(kx) sin(kc) / c.
    a, n = 150.0, 30
    z, x, k = sine_columns(n, a, 7.3)
    expected = np.degrees(np.arctan(np.abs(a * np.cos(k * x) * math.sin(k * CELL) / CELL)))
    got = tf.slope_degrees(z, CELL)
    assert np.allclose(got[1:-1, 1:-1], np.broadcast_to(expected[1:-1], (n - 2, n - 2)), atol=1e-9)


def test_plane_fit_roughness_of_sinusoid_matches_closed_form():
    # 3 x 3 plane fit on y-constant f(-1), f(0), f(1): residual r0 = (2 f0 - f1 - f-1) / 3 at the centre
    # column and -r0/2 at the sides, so RMS = |r0| / sqrt(2) = (sqrt(2)/3) A |sin(kx)| (1 - cos(kc)).
    a, n = 40.0, 30
    z, x, k = sine_columns(n, a, 5.1)
    expected = math.sqrt(2) / 3 * a * np.abs(np.sin(k * x)) * (1 - math.cos(k * CELL))
    got = tf.roughness_rms(z, 3)
    assert np.allclose(got[1:-1, 1:-1], np.broadcast_to(expected[1:-1], (n - 2, n - 2)), atol=1e-9)


def grid_of(z):
    return HarmonizedGrid(elevation_m=z, valid=np.isfinite(z), resolution_m=CELL, cells=z.shape[0])


def tilted_plane(n, angle_deg):
    x = np.arange(n, dtype=float)[None, :] * CELL
    return np.repeat(500.0 + math.tan(math.radians(angle_deg)) * x, n, axis=0)


def one_hot(edges, value):
    i = min(int(np.searchsorted(edges, value, side="right")) - 1, len(edges) - 2)
    out = np.zeros(len(edges) - 1)
    out[i] = 1.0
    return out


def test_flat_and_planar_terrain_have_known_one_hot_distributions_and_scores():
    n = 40
    flat = compute_features(grid_of(np.full((n, n), 1000.0)), "flat")
    # 12 deg, not 10 deg: a value exactly on a bin edge is split between two bins by float rounding.
    tilt = compute_features(grid_of(tilted_plane(n, 12.0)), "tilt")
    relief_tilt = 4 * CELL * math.tan(math.radians(12.0))  # 5 x 5 window spans 4 cells: ~393.7 m
    assert np.array_equal(flat.histograms["slope_distribution"], one_hot(settings.SLOPE_BIN_EDGES_DEG, 0.0))
    assert np.array_equal(flat.histograms["relative_relief"], one_hot(settings.RELIEF_BIN_EDGES_M, 0.0))
    assert np.array_equal(flat.histograms["surface_roughness"], one_hot(settings.ROUGHNESS_BIN_EDGES_M, 0.0))
    assert np.array_equal(tilt.histograms["slope_distribution"], one_hot(settings.SLOPE_BIN_EDGES_DEG, 12.0))
    assert np.array_equal(tilt.histograms["relative_relief"], one_hot(settings.RELIEF_BIN_EDGES_M, relief_tilt))
    assert np.array_equal(tilt.histograms["surface_roughness"], one_hot(settings.ROUGHNESS_BIN_EDGES_M, 0.0))

    s = {m: sim.distribution_similarity(flat.histograms[m], tilt.histograms[m]) for m in METRICS}
    # Disjoint one-hot slope and relief histograms -> 0; both planes have zero roughness -> 1.
    assert s == pytest.approx({"relative_relief": 0.0, "slope_distribution": 0.0, "surface_roughness": 1.0}, abs=1e-12)
    assert sim.total_similarity(s) == pytest.approx(1 / 3, abs=1e-12)
    # Flat against flat scores 1.0 on every metric: a degenerate but finite result.
    assert all(
        sim.distribution_similarity(flat.histograms[m], flat.histograms[m]) == pytest.approx(1.0) for m in METRICS
    )


def test_feature_distributions_are_proper_probability_vectors():
    rng = np.random.default_rng(11)
    z = np.cumsum(np.cumsum(rng.normal(0, 5, (60, 60)), axis=0), axis=1)
    z[10:14, 20:30] = np.nan
    f = compute_features(grid_of(z), "random")
    edges = {
        "relative_relief": settings.RELIEF_BIN_EDGES_M,
        "slope_distribution": settings.SLOPE_BIN_EDGES_DEG,
        "surface_roughness": settings.ROUGHNESS_BIN_EDGES_M,
    }
    for m in METRICS:
        h = np.asarray(f.histograms[m])
        assert h.shape == (len(edges[m]) - 1,)  # shared, fixed bins
        assert np.all(h >= 0) and h.sum() == pytest.approx(1.0, abs=1e-12)
