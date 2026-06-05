"""Column-level profiles computed from raw values.

Everything here works on plain Python sequences and NumPy arrays so it can be
unit-tested without reading a file or constructing a dataframe. The dataframe
layer in :mod:`dsdiff.dataset` adapts polars columns into these calls.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# Canonical dtype groups, so CSV/Parquet/JSON all map onto the same vocabulary.
NUMERIC = "numeric"
CATEGORICAL = "categorical"
BOOLEAN = "boolean"
DATETIME = "datetime"
OTHER = "other"

DEFAULT_BINS = 20


@dataclass(frozen=True, slots=True)
class NumericSummary:
    minimum: float
    maximum: float
    mean: float
    std: float
    edges: tuple[float, ...]
    counts: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ColumnProfile:
    name: str
    kind: str
    count: int
    null_count: int
    n_unique: int
    numeric: NumericSummary | None = None
    top_categories: tuple[tuple[str, int], ...] = field(default_factory=tuple)

    @property
    def null_rate(self) -> float:
        total = self.count + self.null_count
        return self.null_count / total if total else 0.0


def quantile_edges(values: np.ndarray, bins: int = DEFAULT_BINS) -> np.ndarray:
    """Return monotonically increasing bin edges from value quantiles.

    Quantile binning keeps roughly equal mass per bin in the baseline, which
    is what the population stability index expects. Degenerate columns (few
    distinct values) collapse to as many edges as can be made unique.
    """

    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return np.array([0.0, 1.0])
    qs = np.linspace(0.0, 1.0, bins + 1)
    edges = np.quantile(finite, qs)
    edges = np.unique(edges)
    if edges.size < 2:
        lo = float(edges[0])
        edges = np.array([lo, lo + 1.0])
    # Nudge the outer edges so min and max values fall inside the range.
    edges = edges.astype(float)
    edges[0] = np.nextafter(edges[0], -np.inf)
    edges[-1] = np.nextafter(edges[-1], np.inf)
    return edges


def bin_counts(values: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Count finite values per bucket, clamping out-of-range values to the
    edge bins.

    Clamping matters for drift: if a new dataset shifts entirely past the
    baseline's range, the moved mass must land in the outer bins rather than
    being dropped, otherwise a large shift would read as no change.
    """

    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return np.zeros(len(edges) - 1, dtype=int)
    clamped = np.clip(finite, edges[0], edges[-1])
    counts, _ = np.histogram(clamped, bins=edges)
    return counts.astype(int)


def profile_numeric(name: str, values: np.ndarray, *, bins: int = DEFAULT_BINS) -> ColumnProfile:
    arr = np.asarray(values, dtype=float)
    null_count = int(np.count_nonzero(~np.isfinite(arr)))
    finite = arr[np.isfinite(arr)]
    count = int(finite.size)
    if count == 0:
        summary = NumericSummary(0.0, 0.0, 0.0, 0.0, (0.0, 1.0), (0,))
        return ColumnProfile(name, NUMERIC, 0, null_count, 0, numeric=summary)
    edges = quantile_edges(finite, bins=bins)
    counts = bin_counts(finite, edges)
    summary = NumericSummary(
        minimum=float(finite.min()),
        maximum=float(finite.max()),
        mean=float(finite.mean()),
        std=float(finite.std(ddof=0)),
        edges=tuple(float(e) for e in edges),
        counts=tuple(int(c) for c in counts),
    )
    return ColumnProfile(
        name=name,
        kind=NUMERIC,
        count=count,
        null_count=null_count,
        n_unique=int(np.unique(finite).size),
        numeric=summary,
    )


def profile_categorical(
    name: str,
    values: list[str | None],
    *,
    kind: str = CATEGORICAL,
    top_k: int = 20,
) -> ColumnProfile:
    null_count = sum(1 for v in values if v is None)
    present = [str(v) for v in values if v is not None]
    counts: dict[str, int] = {}
    for value in present:
        counts[value] = counts.get(value, 0) + 1
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ColumnProfile(
        name=name,
        kind=kind,
        count=len(present),
        null_count=null_count,
        n_unique=len(counts),
        top_categories=tuple(ordered[:top_k]),
    )


def category_frequencies(profile: ColumnProfile) -> dict[str, float]:
    total = sum(c for _, c in profile.top_categories)
    if total == 0:
        return {}
    return {value: c / total for value, c in profile.top_categories}


def is_finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value)
