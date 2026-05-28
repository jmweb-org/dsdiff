"""Read tabular files and turn them into dataset profiles.

This is the only module that knows about polars and file formats. It adapts
columns into the pure profiling functions in :mod:`dsdiff.profile`, optionally
reusing a baseline's bin edges so a new dataset is binned the same way (which
is what makes the population stability index comparable).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from dsdiff.profile import (
    BOOLEAN,
    CATEGORICAL,
    DATETIME,
    NUMERIC,
    OTHER,
    ColumnProfile,
    NumericSummary,
    bin_counts,
    profile_categorical,
    profile_numeric,
)


@dataclass(frozen=True, slots=True)
class DatasetProfile:
    row_count: int
    columns: dict[str, ColumnProfile]

    def to_dict(self) -> dict:
        return {
            "row_count": self.row_count,
            "columns": {name: _column_to_dict(p) for name, p in self.columns.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> DatasetProfile:
        columns = {
            name: _column_from_dict(name, payload)
            for name, payload in data.get("columns", {}).items()
        }
        return cls(row_count=int(data.get("row_count", 0)), columns=columns)


def read_frame(path: str | Path) -> pl.DataFrame:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pl.read_csv(path)
    if suffix in {".parquet", ".pq"}:
        return pl.read_parquet(path)
    if suffix in {".jsonl", ".ndjson"}:
        return pl.read_ndjson(path)
    if suffix == ".json":
        return pl.read_json(path)
    raise ValueError(f"unsupported file type: {path.suffix or '(none)'}")


def _kind_of(dtype: pl.DataType) -> str:
    if dtype.is_numeric():
        return NUMERIC
    if dtype == pl.Boolean:
        return BOOLEAN
    if dtype in (pl.Utf8, pl.Categorical) or dtype == pl.String:
        return CATEGORICAL
    if dtype in (pl.Date, pl.Time) or isinstance(dtype, pl.Datetime):
        return DATETIME
    return OTHER


def profile_frame(
    frame: pl.DataFrame,
    *,
    edges: dict[str, tuple[float, ...]] | None = None,
) -> DatasetProfile:
    edges = edges or {}
    columns: dict[str, ColumnProfile] = {}
    for name in frame.columns:
        series = frame.get_column(name)
        kind = _kind_of(series.dtype)
        if kind == NUMERIC:
            columns[name] = _profile_numeric_series(name, series, edges.get(name))
        elif kind == BOOLEAN:
            values = ["true" if v else "false" if v is not None else None for v in series.to_list()]
            columns[name] = profile_categorical(name, values, kind=BOOLEAN)
        else:
            values = [None if v is None else str(v) for v in series.to_list()]
            columns[name] = profile_categorical(name, values, kind=kind)
    return DatasetProfile(row_count=frame.height, columns=columns)


def _profile_numeric_series(
    name: str, series: pl.Series, baseline_edges: tuple[float, ...] | None
) -> ColumnProfile:
    arr = series.cast(pl.Float64, strict=False).to_numpy()
    profile = profile_numeric(name, arr)
    if baseline_edges is None or profile.numeric is None:
        return profile
    # Re-bin against the baseline edges so PSI is comparable.
    edges = np.asarray(baseline_edges, dtype=float)
    counts = bin_counts(arr, edges)
    summary = profile.numeric
    rebinned = NumericSummary(
        minimum=summary.minimum,
        maximum=summary.maximum,
        mean=summary.mean,
        std=summary.std,
        edges=tuple(float(e) for e in edges),
        counts=tuple(int(c) for c in counts),
    )
    return ColumnProfile(
        name=profile.name,
        kind=profile.kind,
        count=profile.count,
        null_count=profile.null_count,
        n_unique=profile.n_unique,
        numeric=rebinned,
    )


def profile_file(path: str | Path, *, edges: dict[str, tuple[float, ...]] | None = None):
    return profile_frame(read_frame(path), edges=edges)


def _column_to_dict(profile: ColumnProfile) -> dict:
    out: dict = {
        "kind": profile.kind,
        "count": profile.count,
        "null_count": profile.null_count,
        "n_unique": profile.n_unique,
    }
    if profile.numeric is not None:
        n = profile.numeric
        out["numeric"] = {
            "minimum": n.minimum,
            "maximum": n.maximum,
            "mean": n.mean,
            "std": n.std,
            "edges": list(n.edges),
            "counts": list(n.counts),
        }
    if profile.top_categories:
        out["top_categories"] = [list(item) for item in profile.top_categories]
    return out


def _column_from_dict(name: str, payload: dict) -> ColumnProfile:
    numeric = None
    if "numeric" in payload:
        n = payload["numeric"]
        numeric = NumericSummary(
            minimum=float(n["minimum"]),
            maximum=float(n["maximum"]),
            mean=float(n["mean"]),
            std=float(n["std"]),
            edges=tuple(float(e) for e in n["edges"]),
            counts=tuple(int(c) for c in n["counts"]),
        )
    top = tuple((str(v), int(c)) for v, c in payload.get("top_categories", []))
    return ColumnProfile(
        name=name,
        kind=str(payload["kind"]),
        count=int(payload["count"]),
        null_count=int(payload["null_count"]),
        n_unique=int(payload["n_unique"]),
        numeric=numeric,
        top_categories=top,
    )
