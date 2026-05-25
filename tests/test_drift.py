from __future__ import annotations

import numpy as np
import pytest

from dsdiff.drift import (
    PSI_HIGH,
    Severity,
    psi_from_counts,
    psi_from_frequencies,
    severity_for_psi,
)


def test_identical_distributions_have_zero_psi():
    counts = np.array([10, 20, 30, 40])
    assert psi_from_counts(counts, counts) == pytest.approx(0.0, abs=1e-9)


def test_psi_grows_as_distributions_diverge():
    base = np.array([25, 25, 25, 25])
    mild = np.array([20, 25, 25, 30])
    strong = np.array([1, 1, 1, 97])
    assert psi_from_counts(base, mild) < psi_from_counts(base, strong)


def test_psi_is_symmetric():
    a = np.array([10, 30, 60])
    b = np.array([40, 30, 30])
    assert psi_from_counts(a, b) == pytest.approx(psi_from_counts(b, a))


def test_psi_requires_matching_bins():
    with pytest.raises(ValueError):
        psi_from_counts(np.array([1, 2, 3]), np.array([1, 2]))


def test_psi_handles_empty_side_without_error():
    value = psi_from_counts(np.array([10, 10, 10]), np.array([0, 0, 0]))
    assert np.isfinite(value)


def test_psi_from_frequencies_aligns_on_keys():
    expected = {"a": 0.5, "b": 0.5}
    actual = {"a": 0.5, "c": 0.5}
    assert psi_from_frequencies(expected, actual) > 0


def test_severity_thresholds():
    assert severity_for_psi(0.0) is Severity.LOW
    assert severity_for_psi(0.15) is Severity.MEDIUM
    assert severity_for_psi(PSI_HIGH) is Severity.HIGH
    assert severity_for_psi(1.0) is Severity.HIGH
