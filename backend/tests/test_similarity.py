import math

import numpy as np
import pytest

import settings
import similarity as sim


def test_identical_distributions_are_maximally_similar():
    p = [0.1, 0.2, 0.3, 0.4]
    assert sim.js_distance(p, p) == pytest.approx(0.0, abs=1e-12)
    assert sim.distribution_similarity(p, p) == pytest.approx(1.0)


def test_disjoint_distributions_have_zero_similarity():
    assert sim.js_distance([1, 0, 0], [0, 0, 1]) == pytest.approx(1.0)
    assert sim.distribution_similarity([1, 0, 0], [0, 0, 1]) == pytest.approx(0.0, abs=1e-12)


def test_more_different_distributions_score_lower():
    p = np.array([0.4, 0.3, 0.2, 0.1])
    near = np.array([0.38, 0.32, 0.19, 0.11])
    far = np.array([0.05, 0.1, 0.25, 0.6])
    assert 1.0 > sim.distribution_similarity(p, near) > sim.distribution_similarity(p, far) > 0.0


def test_known_value_base2():
    # JSD([1,0],[0.5,0.5]) in bits: H(M) - (H(P)+H(Q))/2 with M=[0.75,0.25]
    hm = -(0.75 * math.log2(0.75) + 0.25 * math.log2(0.25))
    expected = math.sqrt(hm - 0.5)
    assert sim.js_distance([1, 0], [0.5, 0.5]) == pytest.approx(expected, rel=1e-12)


def test_unnormalized_counts_are_normalized():
    assert sim.js_distance([2, 2], [5, 5]) == pytest.approx(0.0, abs=1e-12)


def test_degenerate_single_bin_distributions():
    assert sim.distribution_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)


@pytest.mark.parametrize(
    "p,q",
    [([0.5, -0.1, 0.6], [1, 0, 0]), ([np.nan, 1], [1, 0]), ([0, 0], [1, 0]), ([1, 0], [1, 0, 0]), ([], [])],
)
def test_invalid_distributions_raise(p, q):
    with pytest.raises(sim.SimilarityError):
        sim.js_distance(p, q)


def test_scores_stay_in_range_for_random_distributions():
    rng = np.random.default_rng(0)
    for _ in range(500):
        p, q = rng.random(11) ** 3, rng.random(11) ** 3
        s = sim.distribution_similarity(p, q)
        assert math.isfinite(s) and 0.0 <= s <= 1.0


def test_total_follows_configured_weights():
    scores = {"relative_relief": 0.9, "slope_distribution": 0.6, "surface_roughness": 0.3}
    assert sim.total_similarity(scores) == pytest.approx(0.6)
    w = {"relative_relief": 2.0, "slope_distribution": 1.0, "surface_roughness": 1.0}
    assert sim.total_similarity(scores, w) == pytest.approx((1.8 + 0.6 + 0.3) / 4)
    assert sum(settings.SCORE_WEIGHTS.values()) == pytest.approx(1.0)


def test_total_rejects_mismatched_metrics():
    with pytest.raises(sim.SimilarityError):
        sim.total_similarity({"relative_relief": 1.0})
