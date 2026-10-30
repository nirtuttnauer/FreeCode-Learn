"""Module 23 — reference solutions."""

from __future__ import annotations

import warnings

import numpy as np


def normalize_rows(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=np.float64)
    norms = np.linalg.norm(a, axis=1, keepdims=True)  # keepdims => (n, 1), broadcastable
    # where= leaves the zero rows untouched instead of producing nan/inf + a warning.
    return np.divide(a, norms, out=np.zeros_like(a), where=norms != 0)


def moving_average(a: np.ndarray, window: int) -> np.ndarray:
    if window < 1:
        raise ValueError(f"window must be >= 1, got {window}")
    a = np.asarray(a, dtype=np.float64)
    if a.size < window:
        return np.empty(0, dtype=np.float64)

    # Prefix sums: each window is one subtraction, so the whole thing is O(n).
    cumulative = np.cumsum(a, dtype=np.float64)
    totals = np.empty(a.size - window + 1, dtype=np.float64)
    totals[0] = cumulative[window - 1]
    totals[1:] = cumulative[window:] - cumulative[:-window]
    return totals / window


def one_hot(labels: np.ndarray, num_classes: int | None = None) -> np.ndarray:
    labels = np.asarray(labels)
    if labels.size == 0:
        return np.zeros((0, num_classes or 0), dtype=np.float64)
    if num_classes is None:
        num_classes = int(labels.max()) + 1
    if labels.min() < 0 or labels.max() >= num_classes:
        raise ValueError(f"labels must be in [0, {num_classes})")
    return np.eye(num_classes, dtype=np.float64)[labels]  # fancy indexing does the work


def pairwise_distances(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.ndim != 2 or b.ndim != 2 or a.shape[1] != b.shape[1]:
        raise ValueError(f"incompatible shapes: {a.shape} and {b.shape}")

    # |x-y|^2 = |x|^2 + |y|^2 - 2 x.y — only an (n, m) intermediate, not (n, m, d).
    a_sq = np.einsum("ij,ij->i", a, a)[:, None]
    b_sq = np.einsum("ij,ij->i", b, b)[None, :]
    squared = a_sq + b_sq - 2 * (a @ b.T)
    np.maximum(squared, 0, out=squared)  # kill tiny negatives from rounding
    distances = np.sqrt(squared)
    if a is b:
        # The expansion computes a self-distance as (x.x + x.x - 2x.x), a subtraction of
        # two nearly equal numbers, so it lands near sqrt(eps) rather than 0. When both
        # sides are literally the same array we know the true answer, so say so.
        np.fill_diagonal(distances, 0.0)
    return distances


def top_k_indices(a: np.ndarray, k: int) -> np.ndarray:
    a = np.asarray(a)
    if k <= 0:
        return np.empty(0, dtype=np.intp)
    if k >= a.size:
        return np.argsort(a, kind="stable")[::-1]

    candidates = np.argpartition(a, -k)[-k:]  # O(n), unordered
    return candidates[np.argsort(a[candidates])[::-1]]  # sort just the k winners


def replace_outliers(a: np.ndarray, n_std: float = 3.0) -> np.ndarray:
    a = np.asarray(a, dtype=np.float64)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN input
        mean = np.nanmean(a)
        std = np.nanstd(a)

    if not np.isfinite(std) or std == 0:
        return a.copy()

    # np.clip propagates NaN, and out= is deliberately NOT used: never touch the input.
    return np.clip(a, mean - n_std * std, mean + n_std * std)


def describe(a: np.ndarray) -> dict[str, float]:
    a = np.asarray(a, dtype=np.float64).ravel()
    valid = a[~np.isnan(a)]
    count = int(valid.size)

    if count == 0:
        nan = float("nan")
        return {
            "count": 0.0, "mean": nan, "std": nan, "min": nan,
            "p25": nan, "p50": nan, "p75": nan, "max": nan,
        }  # fmt: skip

    return {
        "count": float(count),
        "mean": float(valid.mean()),
        # ddof=1 is the SAMPLE std; numpy's default of 0 is the population one.
        "std": float(valid.std(ddof=1)) if count > 1 else float("nan"),
        "min": float(valid.min()),
        "p25": float(np.percentile(valid, 25)),
        "p50": float(np.percentile(valid, 50)),
        "p75": float(np.percentile(valid, 75)),
        "max": float(valid.max()),
    }
