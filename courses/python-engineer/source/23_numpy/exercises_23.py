"""Module 23 exercises.  pytest 23_numpy

Rules for this module:
- No Python loops over elements. Several tests time large inputs and will fail a loop
  even when it returns the right answer.
- Never mutate an input array. The tests check.
- Watch the shape of your INTERMEDIATES, not just the result — a broadcast that produces
  an (n, m, k) temporary is how you allocate 800 GB by accident.
"""

from __future__ import annotations

import numpy as np


def normalize_rows(a: np.ndarray) -> np.ndarray:
    """Scale each row to unit L2 norm.

    >>> normalize_rows(np.array([[3.0, 4.0], [0.0, 0.0]]))
    array([[0.6, 0.8],
           [0. , 0. ]])

    - A zero row stays all zeros — no division by zero, no NaN, and no warning.
    - The result is float, whatever the input dtype.
    - The input is not modified.

    `keepdims=True` is what makes the division broadcast correctly.
    """
    raise NotImplementedError


def moving_average(a: np.ndarray, window: int) -> np.ndarray:
    """Mean of every consecutive `window` values.

    >>> moving_average(np.array([1.0, 2, 3, 4, 5]), 3)
    array([2., 3., 4.])

    - Result length is `len(a) - window + 1`; an input shorter than the window gives an
      empty array.
    - `window < 1` raises ValueError.
    - O(n): use `np.cumsum` (subtract a shifted copy) or
      `np.lib.stride_tricks.sliding_window_view`. The tests run 2,000,000 elements with a
      1,000-wide window, so an O(n*window) version will time out.
    """
    raise NotImplementedError


def one_hot(labels: np.ndarray, num_classes: int | None = None) -> np.ndarray:
    """Turn an integer label vector into a one-hot matrix of shape (len(labels), num_classes).

    >>> one_hot(np.array([0, 2, 1]), 3)
    array([[1., 0., 0.],
           [0., 0., 1.],
           [0., 1., 0.]])

    - `num_classes=None` means `labels.max() + 1`.
    - dtype float64.
    - A label outside [0, num_classes) raises ValueError.
    - Empty input gives shape (0, num_classes).

    Two idiomatic ways: `np.eye(num_classes)[labels]` (fancy indexing) or build zeros and
    assign with `out[np.arange(n), labels] = 1`. Know both.
    """
    raise NotImplementedError


def pairwise_distances(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Euclidean distance between every row of `a` and every row of `b`.

    `a` is (n, d), `b` is (m, d) -> result is (n, m).

    >>> pairwise_distances(np.array([[0.0, 0.0]]), np.array([[3.0, 4.0]]))
    array([[5.]])

    - Mismatched `d` raises ValueError.
    - No loops.

    The obvious broadcast `((a[:, None] - b[None]) ** 2).sum(-1)` allocates an (n, m, d)
    intermediate. For the tests' 2000x2000x50 that is 1.6 GB. Use the expansion instead:

        |x - y|^2 = |x|^2 + |y|^2 - 2 x·y

    which is two norms plus one matmul, and allocates only (n, m). Clip tiny negatives to
    zero before the square root — floating point makes them happen.

    The honest trade-off: that expansion subtracts two nearly equal numbers, so it loses
    precision for SMALL distances. Expect an absolute error around 1e-7, and note that it
    varies between machines because it depends on the BLAS library doing the matmul. (The
    course's own CI caught exactly this: a test asserting 1e-8 passed on one BLAS and
    failed on another.) If both arguments are the same array, `np.fill_diagonal(out, 0)`
    fixes the self-distances exactly. scikit-learn's `euclidean_distances` does the same
    thing for the same reason.
    """
    raise NotImplementedError


def top_k_indices(a: np.ndarray, k: int) -> np.ndarray:
    """Indices of the k largest values, ordered largest first.

    >>> top_k_indices(np.array([5, 1, 9, 3]), 2)
    array([2, 0])

    - `k <= 0` gives an empty int array; `k >= len(a)` gives every index, sorted by value.
    - Ties may resolve either way.
    - Use `np.argpartition` (O(n)) and sort only the k selected values — the tests run
      k=10 over 5,000,000 elements, where a full argsort is much slower.
    """
    raise NotImplementedError


def replace_outliers(a: np.ndarray, n_std: float = 3.0) -> np.ndarray:
    """Return a COPY with values more than `n_std` standard deviations from the mean
    clipped to that boundary.

    - Computed over the whole array (not per axis), ignoring NaN (`np.nanmean`/`np.nanstd`).
    - NaNs are preserved as NaN.
    - A zero-standard-deviation array comes back unchanged.
    - The input must not be modified — the tests assert on that, and `np.clip(a, ..., out=a)`
      is the mistake they're looking for.
    """
    raise NotImplementedError


def describe(a: np.ndarray) -> dict[str, float]:
    """Summary statistics of a 1-D array, NaN-aware.

    Returns `{"count", "mean", "std", "min", "p25", "p50", "p75", "max"}` as floats.

    - `count` is the number of NON-NaN values.
    - `std` is the SAMPLE standard deviation (`ddof=1`); with fewer than 2 values it is
      `nan`. NumPy defaults to `ddof=0` (population), which is the wrong default for a
      sample and a very common silent bug.
    - Percentiles use `np.nanpercentile` with linear interpolation.
    - An all-NaN or empty array gives `count=0` and `nan` everywhere else, without
      raising or warning.
    """
    raise NotImplementedError
