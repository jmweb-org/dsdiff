"""Render findings for the terminal, as Markdown, and as JSON."""

from __future__ import annotations

from rich.console import Group
from rich.table import Table
from rich.text import Text

from dsdiff.compare import Finding
from dsdiff.drift import Severity

_STYLE = {Severity.HIGH: "bold red", Severity.MEDIUM: "yellow", Severity.LOW: "dim"}


def findings_to_json(findings: list[Finding]) -> list[dict]:
    return [
        {
            "column": f.column,
            "kind": f.kind.value,
            "severity": f.severity.value,
            "detail": f.detail,
            "psi": f.psi,
        }
        for f in findings
    ]


def render_terminal(findings: list[Finding]) -> Group:
    if not findings:
        return Group(Text("no differences", style="green"))
    table = Table(box=None, pad_edge=False)
    table.add_column("severity")
    table.add_column("column", style="cyan")
    table.add_column("change")
    table.add_column("detail")
    for f in findings:
        table.add_row(
            Text(f.severity.value, style=_STYLE[f.severity]),
            f.column,
            f.kind.value,
            f.detail,
        )
    return Group(table)


def render_markdown(findings: list[Finding]) -> str:
    if not findings:
        return "No differences found."
    lines = [
        "| severity | column | change | detail |",
        "| --- | --- | --- | --- |",
    ]
    for f in findings:
        lines.append(f"| {f.severity.value} | {f.column} | {f.kind.value} | {f.detail} |")
    return "\n".join(lines)
