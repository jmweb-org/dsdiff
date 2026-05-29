from __future__ import annotations

import polars as pl
import pytest

from dsdiff.dataset import (
    DatasetProfile,
    profile_file,
    profile_frame,
    read_frame,
)
from dsdiff.profile import CATEGORICAL, NUMERIC


def test_profile_frame_classifies_kinds():
    frame = pl.DataFrame({"age": [20, 30, 40], "city": ["a", "b", "a"]})
    profile = profile_frame(frame)
    assert profile.row_count == 3
    assert profile.columns["age"].kind == NUMERIC
    assert profile.columns["city"].kind == CATEGORICAL


def test_profile_frame_reuses_baseline_edges():
    base = pl.DataFrame({"x": [float(i) for i in range(100)]})
    new = pl.DataFrame({"x": [float(i) for i in range(100)]})
    base_profile = profile_frame(base)
    edges = {"x": base_profile.columns["x"].numeric.edges}
    new_profile = profile_frame(new, edges=edges)
    assert new_profile.columns["x"].numeric.edges == edges["x"]


def test_read_csv_round_trips(tmp_path):
    path = tmp_path / "data.csv"
    pl.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]}).write_csv(path)
    frame = read_frame(path)
    assert frame.columns == ["a", "b"]


def test_read_parquet(tmp_path):
    path = tmp_path / "data.parquet"
    pl.DataFrame({"a": [1, 2, 3]}).write_parquet(path)
    assert read_frame(path).height == 3


def test_unsupported_extension_raises(tmp_path):
    path = tmp_path / "data.txt"
    path.write_text("nope")
    with pytest.raises(ValueError):
        read_frame(path)


def test_profile_serialization_round_trip(tmp_path):
    path = tmp_path / "data.csv"
    pl.DataFrame({"x": [1.0, 2.0, 3.0], "g": ["a", "b", "a"]}).write_csv(path)
    profile = profile_file(path)
    restored = DatasetProfile.from_dict(profile.to_dict())
    assert restored.row_count == profile.row_count
    assert restored.columns["x"].numeric.edges == profile.columns["x"].numeric.edges
    assert restored.columns["g"].top_categories == profile.columns["g"].top_categories
