"""Command-line interface for dsdiff."""

from __future__ import annotations

import json
import sys
from enum import Enum
from pathlib import Path

import typer
from rich.console import Console

from dsdiff import __version__
from dsdiff.compare import compare_files, has_blocking
from dsdiff.dataset import profile_file
from dsdiff.drift import Severity
from dsdiff.render import findings_to_json, render_markdown, render_terminal

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Diff two dataset files: schema changes plus column-level drift.",
)
_out = Console()
_err = Console(stderr=True)

EXIT_OK = 0
EXIT_BLOCKING = 1
EXIT_BAD_INPUT = 2


class FailOn(str, Enum):
    high = "high"
    medium = "medium"


def _version_callback(value: bool) -> None:
    if value:
        _out.print(f"dsdiff {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    _version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    """dsdiff command-line interface."""


@app.command("diff")
def diff(
    baseline: Path = typer.Argument(..., help="Baseline dataset, or a saved profile JSON."),
    candidate: Path = typer.Argument(..., help="Dataset to compare against the baseline."),
    as_json: bool = typer.Option(False, "--json", help="Emit findings as JSON."),
    markdown: bool = typer.Option(False, "--markdown", help="Emit a Markdown table."),
    check: bool = typer.Option(False, "--check", help="Exit non-zero on blocking findings."),
    fail_on: FailOn = typer.Option(
        FailOn.high, "--fail-on", help="Severity that --check treats as blocking."
    ),
) -> None:
    """Compare two datasets and report schema and distribution changes."""

    try:
        findings = compare_files(baseline, candidate)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        _err.print(f"dsdiff: {exc}")
        raise typer.Exit(EXIT_BAD_INPUT) from exc

    if as_json:
        _out.print_json(json.dumps(findings_to_json(findings)))
    elif markdown:
        _out.print(render_markdown(findings))
    else:
        _out.print(render_terminal(findings))

    threshold = Severity.HIGH if fail_on is FailOn.high else Severity.MEDIUM
    if check and has_blocking(findings, threshold):
        raise typer.Exit(EXIT_BLOCKING)


@app.command("profile")
def profile(
    dataset: Path = typer.Argument(..., help="Dataset to profile."),
    output: Path | None = typer.Option(
        None, "-o", "--output", help="Write the profile JSON here (default: stdout)."
    ),
) -> None:
    """Write a committable baseline profile of a dataset."""

    try:
        prof = profile_file(dataset)
    except (OSError, ValueError) as exc:
        _err.print(f"dsdiff: {exc}")
        raise typer.Exit(EXIT_BAD_INPUT) from exc
    payload = json.dumps(prof.to_dict(), indent=2)
    if output is None:
        _out.print_json(payload)
    else:
        Path(output).write_text(payload + "\n", encoding="utf-8")
        _err.print(f"dsdiff: wrote {output}")


def entrypoint() -> None:
    try:
        app()
    except KeyboardInterrupt:  # pragma: no cover - interactive only
        print("dsdiff: interrupted", file=sys.stderr)
        raise SystemExit(130) from None
