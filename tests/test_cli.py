from __future__ import annotations

import json

import polars as pl
from typer.testing import CliRunner

from dsdiff import __version__
from dsdiff import cli as cli_module

runner = CliRunner()


def _csv(tmp_path, name, frame):
    path = tmp_path / name
    frame.write_csv(path)
    return path


def test_version():
    result = runner.invoke(cli_module.app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_diff_identical_reports_no_differences(tmp_path):
    frame = pl.DataFrame({"x": [1, 2, 3], "g": ["a", "b", "a"]})
    a = _csv(tmp_path, "a.csv", frame)
    b = _csv(tmp_path, "b.csv", frame)
    result = runner.invoke(cli_module.app, ["diff", str(a), str(b)])
    assert result.exit_code == 0
    assert "no differences" in result.stdout


def test_diff_added_column_json(tmp_path):
    a = _csv(tmp_path, "a.csv", pl.DataFrame({"x": [1, 2, 3]}))
    b = _csv(tmp_path, "b.csv", pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
    result = runner.invoke(cli_module.app, ["diff", str(a), str(b), "--json"])
    assert result.exit_code == 0
    findings = json.loads(result.stdout)
    assert any(f["kind"] == "column_added" and f["column"] == "y" for f in findings)


def test_diff_check_fails_on_schema_change(tmp_path):
    a = _csv(tmp_path, "a.csv", pl.DataFrame({"x": [1, 2, 3]}))
    b = _csv(tmp_path, "b.csv", pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
    result = runner.invoke(cli_module.app, ["diff", str(a), str(b), "--check"])
    assert result.exit_code == cli_module.EXIT_BLOCKING


def test_diff_markdown_output(tmp_path):
    a = _csv(tmp_path, "a.csv", pl.DataFrame({"x": [1, 2, 3]}))
    b = _csv(tmp_path, "b.csv", pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
    result = runner.invoke(cli_module.app, ["diff", str(a), str(b), "--markdown"])
    assert result.exit_code == 0
    assert "| severity |" in result.stdout


def test_profile_then_diff_against_baseline(tmp_path):
    data = _csv(tmp_path, "data.csv", pl.DataFrame({"x": [float(i) for i in range(50)]}))
    baseline = tmp_path / "baseline.json"
    result = runner.invoke(cli_module.app, ["profile", str(data), "-o", str(baseline)])
    assert result.exit_code == 0
    assert baseline.exists()

    shifted = _csv(
        tmp_path, "shifted.csv", pl.DataFrame({"x": [float(i) + 1000 for i in range(50)]})
    )
    result = runner.invoke(cli_module.app, ["diff", str(baseline), str(shifted), "--json"])
    assert result.exit_code == 0
    findings = json.loads(result.stdout)
    assert any(f["kind"] == "drift" for f in findings)


def test_diff_missing_file_is_bad_input(tmp_path):
    a = _csv(tmp_path, "a.csv", pl.DataFrame({"x": [1, 2, 3]}))
    result = runner.invoke(cli_module.app, ["diff", str(a), str(tmp_path / "missing.csv")])
    assert result.exit_code == cli_module.EXIT_BAD_INPUT
