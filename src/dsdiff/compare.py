"""Turn two dataset profiles into an ordered list of findings.

A finding is one human-readable difference with a severity. The high-level
:func:`compare_files` ties it together: it profiles the baseline, bins the new
dataset against the baseline's edges so drift is comparable, and runs the
comparison. The baseline may be a data file or a previously saved profile JSON.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from dsdiff.dataset import DatasetProfile, profile_file
from dsdiff.drift import (
    Severity,
    psi_from_counts,
    psi_from_frequencies,
    severity_for_psi,
)
from dsdiff.profile import NUMERIC, ColumnProfile, category_frequencies

_NULL_RATE_HIGH = 0.2
_NULL_RATE_MEDIUM = 0.05
_SEVERITY_ORDER = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}


class FindingKind(str, Enum):
    COLUMN_ADDED = "column_added"
    COLUMN_REMOVED = "column_removed"
    TYPE_CHANGED = "type_changed"
    NULL_RATE = "null_rate"
    CARDINALITY = "cardinality"
    DRIFT = "drift"


@dataclass(frozen=True, slots=True)
class Finding:
    column: str
    kind: FindingKind
    severity: Severity
    detail: str
    psi: float | None = None

    @property
    def sort_key(self) -> tuple[int, str]:
        return (_SEVERITY_ORDER[self.severity], self.column)


def compare_profiles(old: DatasetProfile, new: DatasetProfile) -> list[Finding]:
    findings: list[Finding] = []
    old_cols = set(old.columns)
    new_cols = set(new.columns)

    for name in sorted(new_cols - old_cols):
        findings.append(Finding(name, FindingKind.COLUMN_ADDED, Severity.HIGH, "new column"))
    for name in sorted(old_cols - new_cols):
        findings.append(Finding(name, FindingKind.COLUMN_REMOVED, Severity.HIGH, "column removed"))

    for name in sorted(old_cols & new_cols):
        findings.extend(_compare_column(old.columns[name], new.columns[name]))

    findings.sort(key=lambda f: f.sort_key)
    return findings


def _compare_column(old: ColumnProfile, new: ColumnProfile) -> list[Finding]:
    if old.kind != new.kind:
        return [
            Finding(
                old.name,
                FindingKind.TYPE_CHANGED,
                Severity.HIGH,
                f"{old.kind} -> {new.kind}",
            )
        ]

    findings: list[Finding] = []
    findings.extend(_null_rate_finding(old, new))
    findings.extend(_cardinality_finding(old, new))
    findings.extend(_drift_finding(old, new))
    return findings


def _null_rate_finding(old: ColumnProfile, new: ColumnProfile) -> list[Finding]:
    delta = abs(new.null_rate - old.null_rate)
    if delta >= _NULL_RATE_HIGH:
        severity = Severity.HIGH
    elif delta >= _NULL_RATE_MEDIUM:
        severity = Severity.MEDIUM
    else:
        return []
    return [
        Finding(
            old.name,
            FindingKind.NULL_RATE,
            severity,
            f"null rate {old.null_rate:.1%} -> {new.null_rate:.1%}",
        )
    ]


def _cardinality_finding(old: ColumnProfile, new: ColumnProfile) -> list[Finding]:
    if old.kind == NUMERIC or old.n_unique == 0:
        return []
    ratio = new.n_unique / old.n_unique
    if ratio >= 2.0 or ratio <= 0.5:
        return [
            Finding(
                old.name,
                FindingKind.CARDINALITY,
                Severity.MEDIUM,
                f"distinct values {old.n_unique} -> {new.n_unique}",
            )
        ]
    return []


def _drift_finding(old: ColumnProfile, new: ColumnProfile) -> list[Finding]:
    if old.kind == NUMERIC and old.numeric and new.numeric:
        psi = psi_from_counts(old.numeric.counts, new.numeric.counts)
    else:
        psi = psi_from_frequencies(category_frequencies(old), category_frequencies(new))
    severity = severity_for_psi(psi)
    if severity is Severity.LOW:
        return []
    return [
        Finding(
            old.name,
            FindingKind.DRIFT,
            severity,
            f"PSI {psi:.3f}",
            psi=psi,
        )
    ]


def has_blocking(findings: list[Finding], threshold: Severity = Severity.HIGH) -> bool:
    limit = _SEVERITY_ORDER[threshold]
    return any(_SEVERITY_ORDER[f.severity] <= limit for f in findings)


def _load_baseline(path: Path) -> tuple[DatasetProfile, dict[str, tuple[float, ...]]]:
    if path.suffix.lower() == ".json":
        profile = DatasetProfile.from_dict(json.loads(path.read_text(encoding="utf-8")))
    else:
        profile = profile_file(path)
    edges = {
        name: col.numeric.edges for name, col in profile.columns.items() if col.numeric is not None
    }
    return profile, edges


def compare_files(baseline: str | Path, candidate: str | Path) -> list[Finding]:
    """Profile both inputs and return findings, highest severity first."""

    old_profile, edges = _load_baseline(Path(baseline))
    new_profile = profile_file(candidate, edges=edges)
    return compare_profiles(old_profile, new_profile)
