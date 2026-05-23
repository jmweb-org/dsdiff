from __future__ import annotations

import numpy as np

from dsdiff.profile import (
    NUMERIC,
    bin_counts,
    category_frequencies,
    profile_categorical,
    profile_numeric,
    quantile_edges,
)


def test_profile_numeric_basic_stats():
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    p = profile_numeric("x", values)
    assert p.kind == NUMERIC
    assert p.count == 5
    assert p.null_count == 0
    assert p.numeric.minimum == 1.0
    assert p.numeric.maximum == 5.0
    assert p.numeric.mean == 3.0


def test_profile_numeric_counts_nulls():
    values = np.array([1.0, np.nan, 3.0, np.nan])
    p = profile_numeric("x", values)
    assert p.null_count == 2
    assert p.count == 2


def test_quantile_edges_are_monotonic_and_cover_values():
    values = np.array([float(i) for i in range(100)])
    edges = quantile_edges(values, bins=10)
    assert np.all(np.diff(edges) > 0)
    assert edges[0] < values.min()
    assert edges[-1] > values.max()


def test_quantile_edges_handles_constant_column():
    edges = quantile_edges(np.array([7.0, 7.0, 7.0]), bins=10)
    assert edges.size >= 2
    assert np.all(np.diff(edges) > 0)


def test_bin_counts_sum_to_finite_value_count():
    values = np.array([1.0, 2.0, 3.0, 4.0, np.nan])
    edges = quantile_edges(values, bins=4)
    counts = bin_counts(values, edges)
    assert counts.sum() == 4


def test_profile_categorical_top_and_cardinality():
    values = ["a", "a", "b", None, "c", "a"]
    p = profile_categorical("c", values)
    assert p.null_count == 1
    assert p.count == 5
    assert p.n_unique == 3
    assert p.top_categories[0] == ("a", 3)


def test_category_frequencies_normalize_to_one():
    p = profile_categorical("c", ["a", "a", "b", "b"])
    freqs = category_frequencies(p)
    assert sum(freqs.values()) == 1.0
    assert freqs["a"] == 0.5
