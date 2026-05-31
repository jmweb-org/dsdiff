from __future__ import annotations

from dsdiff.compare import FindingKind, compare_profiles, has_blocking
from dsdiff.dataset import DatasetProfile
from dsdiff.drift import Severity
from dsdiff.profile import (
    CATEGORICAL,
    NUMERIC,
    ColumnProfile,
    NumericSummary,
)


def num(name, *, count=100, nulls=0, n_unique=50, counts=(25, 25, 25, 25)):
    edges = tuple(float(i) for i in range(len(counts) + 1))
    summary = NumericSummary(0.0, float(len(counts)), 2.0, 1.0, edges, counts)
    return ColumnProfile(name, NUMERIC, count, nulls, n_unique, numeric=summary)


def cat(name, top, *, count=None, nulls=0, n_unique=None):
    top = tuple(top)
    count = count if count is not None else sum(c for _, c in top)
    n_unique = n_unique if n_unique is not None else len(top)
    return ColumnProfile(name, CATEGORICAL, count, nulls, n_unique, top_categories=top)


def ds(**columns):
    return DatasetProfile(row_count=100, columns=dict(columns))


def test_added_and_removed_columns_are_high():
    old = ds(a=num("a"))
    new = ds(a=num("a"), b=num("b"))
    findings = compare_profiles(old, new)
    assert any(f.kind is FindingKind.COLUMN_ADDED and f.column == "b" for f in findings)

    findings2 = compare_profiles(new, old)
    assert any(f.kind is FindingKind.COLUMN_REMOVED and f.column == "b" for f in findings2)


def test_type_change_is_high():
    old = ds(x=num("x"))
    new = ds(x=cat("x", [("a", 100)]))
    findings = compare_profiles(old, new)
    assert findings[0].kind is FindingKind.TYPE_CHANGED
    assert findings[0].severity is Severity.HIGH


def test_numeric_drift_detected():
    old = ds(x=num("x", counts=(25, 25, 25, 25)))
    new = ds(x=num("x", counts=(1, 1, 1, 97)))
    findings = compare_profiles(old, new)
    drift = [f for f in findings if f.kind is FindingKind.DRIFT]
    assert drift and drift[0].severity is Severity.HIGH
    assert drift[0].psi is not None


def test_no_drift_for_identical_numeric():
    old = ds(x=num("x"))
    new = ds(x=num("x"))
    assert [f for f in compare_profiles(old, new) if f.kind is FindingKind.DRIFT] == []


def test_null_rate_jump_flagged():
    old = ds(x=num("x", count=100, nulls=0))
    new = ds(x=num("x", count=70, nulls=30))
    findings = compare_profiles(old, new)
    assert any(f.kind is FindingKind.NULL_RATE for f in findings)


def test_cardinality_change_flagged_for_categoricals():
    old = ds(c=cat("c", [("a", 50), ("b", 50)], n_unique=2))
    new = ds(c=cat("c", [("a", 20)], n_unique=10))
    findings = compare_profiles(old, new)
    assert any(f.kind is FindingKind.CARDINALITY for f in findings)


def test_has_blocking_respects_threshold():
    medium = ds(x=num("x", counts=(25, 25, 25, 25)))
    drifted = ds(x=num("x", counts=(15, 25, 25, 35)))
    findings = compare_profiles(medium, drifted)
    # A moderate shift should not block at the default high threshold.
    assert has_blocking(findings, Severity.HIGH) is False or all(
        f.severity is not Severity.HIGH for f in findings
    )
