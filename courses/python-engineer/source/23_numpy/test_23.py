import time

import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_array_equal

from courselib import impl

m = impl("23")
rng = np.random.default_rng(0)


def timed(fn) -> float:
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


class TestNormalizeRows:
    def test_unit_norms(self):
        got = m.normalize_rows(np.array([[3.0, 4.0], [1.0, 0.0]]))
        assert_allclose(got, [[0.6, 0.8], [1.0, 0.0]])

    def test_every_row_has_norm_one(self):
        got = m.normalize_rows(rng.random((20, 5)))
        assert_allclose(np.linalg.norm(got, axis=1), np.ones(20))

    def test_zero_row_stays_zero(self):
        got = m.normalize_rows(np.array([[0.0, 0.0], [3.0, 4.0]]))
        assert_array_equal(got[0], [0.0, 0.0])
        assert not np.isnan(got).any()

    def test_no_warning_on_zero_rows(self):
        with np.errstate(all="raise"):
            m.normalize_rows(np.zeros((3, 4)))

    def test_integer_input_becomes_float(self):
        assert m.normalize_rows(np.array([[3, 4]])).dtype == np.float64

    def test_input_is_not_modified(self):
        a = np.array([[3.0, 4.0]])
        m.normalize_rows(a)
        assert_array_equal(a, [[3.0, 4.0]])

    def test_single_row(self):
        assert_allclose(m.normalize_rows(np.array([[0.0, 5.0]])), [[0.0, 1.0]])


class TestMovingAverage:
    def test_basic(self):
        assert_allclose(m.moving_average(np.array([1.0, 2, 3, 4, 5]), 3), [2.0, 3.0, 4.0])

    def test_window_of_one_is_identity(self):
        a = np.array([1.0, 2, 3])
        assert_allclose(m.moving_average(a, 1), a)

    def test_result_length(self):
        assert m.moving_average(rng.random(100), 10).shape == (91,)

    def test_input_shorter_than_window(self):
        assert m.moving_average(np.array([1.0, 2]), 5).size == 0

    def test_window_equals_length(self):
        assert_allclose(m.moving_average(np.array([1.0, 2, 3]), 3), [2.0])

    def test_rejects_bad_window(self):
        with pytest.raises(ValueError):
            m.moving_average(np.arange(5.0), 0)

    def test_matches_bruteforce(self):
        a = rng.random(200)
        expected = [a[i : i + 7].mean() for i in range(len(a) - 6)]
        assert_allclose(m.moving_average(a, 7), expected)

    def test_is_linear_in_n_not_n_times_window(self):
        a = rng.random(2_000_000)
        assert timed(lambda: m.moving_average(a, 1_000)) < 1.0

    def test_numerically_sane_on_large_input(self):
        a = np.ones(100_000)
        assert_allclose(m.moving_average(a, 100), np.ones(99_901), atol=1e-9)


class TestOneHot:
    def test_basic(self):
        assert_array_equal(
            m.one_hot(np.array([0, 2, 1]), 3),
            [[1, 0, 0], [0, 0, 1], [0, 1, 0]],
        )

    def test_infers_num_classes(self):
        assert m.one_hot(np.array([0, 3])).shape == (2, 4)

    def test_dtype(self):
        assert m.one_hot(np.array([0, 1])).dtype == np.float64

    def test_rows_sum_to_one(self):
        labels = rng.integers(0, 10, size=100)
        assert_allclose(m.one_hot(labels, 10).sum(axis=1), np.ones(100))

    def test_empty(self):
        assert m.one_hot(np.array([], dtype=int), 5).shape == (0, 5)

    @pytest.mark.parametrize("labels", [[3], [-1]])
    def test_out_of_range(self, labels):
        with pytest.raises(ValueError):
            m.one_hot(np.array(labels), 3)

    def test_large_input(self):
        labels = rng.integers(0, 50, size=200_000)
        assert timed(lambda: m.one_hot(labels, 50)) < 1.0


class TestPairwiseDistances:
    def test_simple(self):
        assert_allclose(
            m.pairwise_distances(np.array([[0.0, 0.0]]), np.array([[3.0, 4.0]])), [[5.0]]
        )

    def test_shape(self):
        assert m.pairwise_distances(rng.random((4, 3)), rng.random((7, 3))).shape == (4, 7)

    def test_distance_to_self_is_zero(self):
        # atol is 1e-6, not 1e-8, on purpose: the |x|^2 + |y|^2 - 2x.y expansion subtracts
        # nearly equal numbers, so small distances carry ~sqrt(eps) error — and how much
        # depends on which BLAS is installed. Demanding 1e-8 makes this pass on one
        # machine and fail on another, which is worse than useless.
        a = rng.random((10, 4))
        assert_allclose(np.diag(m.pairwise_distances(a, a)), np.zeros(10), atol=1e-6)

    def test_no_negative_distances(self):
        a = rng.random((50, 3))
        assert (m.pairwise_distances(a, a) >= 0).all()

    def test_matches_bruteforce(self):
        a, b = rng.random((8, 3)), rng.random((5, 3))
        expected = np.array([[np.linalg.norm(x - y) for y in b] for x in a])
        assert_allclose(m.pairwise_distances(a, b), expected, atol=1e-6)

    def test_dimension_mismatch(self):
        with pytest.raises(ValueError):
            m.pairwise_distances(rng.random((3, 2)), rng.random((3, 5)))

    def test_input_not_modified(self):
        a = rng.random((4, 3))
        original = a.copy()
        m.pairwise_distances(a, a)
        assert_array_equal(a, original)

    def test_memory_bounded(self):
        # The naive (n, m, d) broadcast would allocate ~1.6 GB here.
        import tracemalloc

        a, b = rng.random((2000, 50)), rng.random((2000, 50))
        tracemalloc.start()
        m.pairwise_distances(a, b)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        assert peak < 200_000_000, f"peaked at {peak / 1e6:.0f} MB — check your intermediates"


class TestTopKIndices:
    def test_basic(self):
        assert_array_equal(m.top_k_indices(np.array([5, 1, 9, 3]), 2), [2, 0])

    def test_ordered_largest_first(self):
        a = rng.random(100)
        got = m.top_k_indices(a, 5)
        assert_allclose(a[got], np.sort(a[got])[::-1])

    def test_selects_the_actual_largest(self):
        a = rng.random(1000)
        assert set(a[m.top_k_indices(a, 10)]) == set(np.sort(a)[-10:])

    def test_k_zero(self):
        assert m.top_k_indices(np.array([1, 2]), 0).size == 0

    def test_k_larger_than_input(self):
        assert_array_equal(m.top_k_indices(np.array([1, 3, 2]), 10), [1, 2, 0])

    def test_returns_indices_not_values(self):
        got = m.top_k_indices(np.array([5, 1, 9]), 1)
        assert got.dtype.kind == "i"
        assert got[0] == 2

    def test_is_fast_for_small_k_over_a_big_array(self):
        a = rng.random(5_000_000)
        assert timed(lambda: m.top_k_indices(a, 10)) < 0.5


class TestReplaceOutliers:
    def test_clips_extremes(self):
        a = np.array([1.0, 2.0, 3.0, 1000.0])
        got = m.replace_outliers(a, n_std=1.0)
        assert got[3] < 1000.0

    def test_leaves_normal_values_alone(self):
        a = rng.normal(size=1000)
        got = m.replace_outliers(a, n_std=5.0)
        assert_allclose(got, a)

    def test_does_not_modify_the_input(self):
        a = np.array([1.0, 2.0, 1000.0])
        original = a.copy()
        m.replace_outliers(a, n_std=1.0)
        assert_array_equal(a, original)

    def test_returns_a_new_array(self):
        a = np.array([1.0, 2.0, 3.0])
        assert m.replace_outliers(a) is not a

    def test_preserves_nan(self):
        a = np.array([1.0, np.nan, 2.0, 500.0])
        got = m.replace_outliers(a, n_std=1.0)
        assert np.isnan(got[1])

    def test_constant_array_unchanged(self):
        a = np.full(10, 7.0)
        assert_allclose(m.replace_outliers(a), a)

    def test_all_nan(self):
        a = np.full(5, np.nan)
        assert np.isnan(m.replace_outliers(a)).all()


class TestDescribe:
    def test_basic(self):
        got = m.describe(np.array([1.0, 2.0, 3.0, 4.0]))
        assert got["count"] == 4
        assert got["mean"] == pytest.approx(2.5)
        assert got["min"] == 1.0
        assert got["max"] == 4.0
        assert got["p50"] == pytest.approx(2.5)

    def test_uses_the_sample_standard_deviation(self):
        got = m.describe(np.array([1.0, 2.0, 3.0, 4.0]))
        assert got["std"] == pytest.approx(np.std([1, 2, 3, 4], ddof=1))
        assert got["std"] != pytest.approx(np.std([1, 2, 3, 4]))

    def test_ignores_nan(self):
        got = m.describe(np.array([1.0, np.nan, 3.0]))
        assert got["count"] == 2
        assert got["mean"] == pytest.approx(2.0)

    def test_single_value_has_nan_std(self):
        got = m.describe(np.array([5.0]))
        assert got["count"] == 1
        assert np.isnan(got["std"])

    def test_empty(self):
        got = m.describe(np.array([]))
        assert got["count"] == 0
        assert all(np.isnan(v) for k, v in got.items() if k != "count")

    def test_all_nan(self):
        got = m.describe(np.array([np.nan, np.nan]))
        assert got["count"] == 0

    def test_no_warnings_on_all_nan(self):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            m.describe(np.array([np.nan]))

    def test_all_values_are_python_floats(self):
        got = m.describe(np.array([1.0, 2.0]))
        assert all(type(v) is float for v in got.values())

    def test_keys(self):
        assert set(m.describe(np.array([1.0]))) == {
            "count", "mean", "std", "min", "p25", "p50", "p75", "max",
        }  # fmt: skip

    def test_percentiles_are_ordered(self):
        got = m.describe(rng.random(1000))
        assert got["min"] <= got["p25"] <= got["p50"] <= got["p75"] <= got["max"]
