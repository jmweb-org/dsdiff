"""Distribution-drift measures.

The population stability index (PSI) is the workhorse: a single number that
summarizes how far a new distribution has moved from a baseline. It is cheap,
interpretable, and the de-facto standard for tabular monitoring. All functions
are pure and operate on counts, so they are exhaustively unit-tested.
"""

from __future__ import annotations

from enum import Enum

import numpy as np

# Conventional PSI thresholds used across the industry.
PSI_MEDIUM = 0.1
PSI_HIGH = 0.25

_EPSILON = 1e-6


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def _normalize(counts: np.ndarray) -> np.ndarray:
    total = counts.sum()
    if total <= 0:
        # Uniform fallback keeps PSI finite when a side is empty.
        return np.full(counts.shape, 1.0 / counts.size)
    fractions = counts / total
    return np.clip(fractions, _EPSILON, None)


def psi_from_counts(expected: np.ndarray, actual: np.ndarray) -> float:
    """Population stability index between two binned distributions."""

    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    if expected.shape != actual.shape:
        raise ValueError("expected and actual must have the same number of bins")
    e = _normalize(expected)
    a = _normalize(actual)
    return float(np.sum((a - e) * np.log(a / e)))


def psi_from_frequencies(expected: dict[str, float], actual: dict[str, float]) -> float:
    """PSI over categorical frequency maps, aligned on the union of keys."""

    keys = sorted(set(expected) | set(actual))
    e = np.array([expected.get(k, 0.0) for k in keys], dtype=float)
    a = np.array([actual.get(k, 0.0) for k in keys], dtype=float)
    return psi_from_counts(e, a)


def severity_for_psi(psi: float) -> Severity:
    if psi >= PSI_HIGH:
        return Severity.HIGH
    if psi >= PSI_MEDIUM:
        return Severity.MEDIUM
    return Severity.LOW
