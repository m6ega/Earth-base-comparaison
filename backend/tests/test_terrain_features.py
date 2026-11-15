"""Terrain mathematics against analytic surfaces with known answers."""

import math

import numpy as np
import pytest

import terrain_features as tf

CELL = 463.0


def plane(n, gx, gy, cell=CELL, offset=0.0):
    """z = offset + gx * east + gy * north on an n x n grid (row 0 = north)."""
    idx = np.arange(n, dtype=np.float64)
    east = idx[None, :] * cell
    north = -idx[:, None] * cell
    return offset + gx * east + gy * north


def interior(a, k=1):
    return a[k:-k, k:-k]


def test_constant_surface_has_zero_slope_relief_and_roughness():
    z = np.full((20, 20), 1234.5)
    assert np.allclose(interior(tf.slope_degrees(z, CELL)), 0.0)
    assert np.allclose(interior(tf.local_relief(z, 5), 2), 0.0)
    assert np.allclose(interior(tf.roughness_rms(z, 3)), 0.0)


def test_borders_without_full_neighbourhood_are_invalid():
    z = np.zeros((10, 10))
    s = tf.slope_degrees(z, CELL)
    assert np.isnan(s[0]).all() and np.isnan(s[-1]).all() and np.isnan(s[:, 0]).all()
    assert np.isfinite(interior(s)).all()


@pytest.mark.parametrize("angle", [0.5, 5.0, 20.0, 45.0, 70.0])
def test_known_linear_slope_along_x(angle):
    g = math.tan(math.radians(angle))
    s = tf.slope_degrees(plane(15, g, 0.0), CELL)
    assert np.allclose(interior(s), angle, atol=1e-9)


def test_known_oblique_slope():
    gx, gy = 0.03, -0.04  # |gradient| = 0.05
    s = tf.slope_degrees(plane(15, gx, gy), CELL)
    assert np.allclose(interior(s), math.degrees(math.atan(0.05)), atol=1e-9)


def test_slope_uses_physical_cell_size():
    z = plane(15, 0.1, 0.0, cell=100.0)  # 10 m rise per 100 m cell
    assert np.allclose(interior(tf.slope_degrees(z, 100.0)), math.degrees(math.atan(0.1)))
    # The same array interpreted with 200 m cells has half the gradient.
    assert np.allclose(interior(tf.slope_degrees(z, 200.0)), math.degrees(math.atan(0.05)))


def test_relief_on_plane_equals_window_span_times_gradient():
    g = 0.02
    r = tf.local_relief(plane(20, g, 0.0), 5)
    assert np.allclose(interior(r, 2), 4 * CELL * g)


def test_known_elevation_range_matches_bruteforce():
    rng = np.random.default_rng(42)
    z = rng.normal(0, 50, (12, 12))
    r = tf.local_relief(z, 5)
    for i in range(2, 10):
        for j in range(2, 10):
            win = z[i - 2 : i + 3, j - 2 : j + 3]
            assert r[i, j] == pytest.approx(win.max() - win.min())


def test_relief_and_roughness_are_offset_invariant():
    rng = np.random.default_rng(1)
    z = rng.normal(0, 30, (16, 16))
    for f, k in ((lambda a: tf.local_relief(a, 5), 2), (lambda a: tf.roughness_rms(a, 3), 1)):
        assert np.allclose(interior(f(z), k), interior(f(z - 4500.0), k), atol=1e-9)


def test_roughness_is_zero_on_tilted_plane():
    z = plane(15, 0.3, -0.2)
    assert np.allclose(interior(tf.roughness_rms(z, 3)), 0.0, atol=1e-9)


def test_roughness_matches_independent_least_squares_on_rugged_surface():
    rng = np.random.default_rng(7)
    z = plane(14, 0.05, 0.02) + rng.normal(0, 10, (14, 14))
    rough = tf.roughness_rms(z, 3)
    offs = np.array([-1.0, 0.0, 1.0])
    xx, yy = np.meshgrid(offs, offs)
    design = np.column_stack([np.ones(9), xx.ravel(), yy.ravel()])
    for i in range(1, 13):
        for j in range(1, 13):
            win = z[i - 1 : i + 2, j - 1 : j + 2].ravel()
            coef, *_ = np.linalg.lstsq(design, win, rcond=None)
            expected = math.sqrt(np.mean((win - design @ coef) ** 2))
            assert rough[i, j] == pytest.approx(expected, rel=1e-9, abs=1e-9)


def test_roughness_scales_linearly_with_amplitude():
    checker = np.indices((12, 12)).sum(axis=0) % 2 * 2.0 - 1.0  # +-1 checkerboard
    r1 = interior(tf.roughness_rms(10.0 * checker, 3))
    r2 = interior(tf.roughness_rms(20.0 * checker, 3))
    assert np.all(r1 > 0)
    assert np.allclose(r2, 2 * r1)


def test_nodata_invalidates_only_its_neighbourhood():
    z = plane(12, 0.01, 0.0)
    z[6, 6] = np.nan
    s = tf.slope_degrees(z, CELL)
    assert np.isnan(s[5:8, 5:8]).all()
    mask = np.ones_like(s, dtype=bool)
    mask[5:8, 5:8] = False
    assert np.isfinite(interior(s)[interior(mask)]).all()


def test_numerical_stability_with_large_absolute_elevations():
    base = plane(15, 0.05, 0.0)
    s0 = tf.slope_degrees(base, CELL)
    s1 = tf.slope_degrees(base + 8_000.0, CELL)
    assert np.allclose(interior(s0), interior(s1), atol=1e-9)
    r = tf.roughness_rms(base + 8_000.0, 3)
    assert np.allclose(interior(r), 0.0, atol=1e-6)


def test_histogram_fractions_shared_edges_and_clipping():
    edges = [0.0, 1.0, 2.0, 4.0]
    frac, n = tf.histogram_fractions(np.array([0.5, 1.5, 3.0, 99.0, np.nan, -0.0]), edges)
    assert n == 5
    assert frac.sum() == pytest.approx(1.0)
    assert list(frac) == pytest.approx([0.4, 0.2, 0.4])  # 99 counted in the last bin


def test_histogram_of_empty_input():
    frac, n = tf.histogram_fractions(np.array([np.nan]), [0.0, 1.0])
    assert n == 0 and frac.sum() == 0.0


def test_invalid_window_and_edges_rejected():
    with pytest.raises(ValueError):
        tf.local_relief(np.zeros((5, 5)), 4)
    with pytest.raises(ValueError):
        tf.histogram_fractions(np.zeros(3), [0.0, 0.0, 1.0])
