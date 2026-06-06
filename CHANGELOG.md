# Changelog

All notable changes to this project are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-06-08

### Added
- `--fail-on medium` to tighten the `--check` gate beyond high-severity only.
- Markdown output for pasting a diff into a pull request.
- Docker image and a published container entry point.
- Continuous integration across Python 3.10, 3.11 and 3.12.

### Fixed
- Drift is no longer missed when a column shifts entirely past the baseline
  range; out-of-range values are clamped to the edge bins.

## [0.1.0] - 2026-06-03

### Added
- `diff` command: schema changes (added, removed, retyped columns), null-rate
  jumps, cardinality changes, and per-column distribution drift via PSI.
- `profile` command: write a committable baseline profile with bin edges so a
  later diff measures drift against the same buckets.
- CSV, Parquet and JSON Lines input through polars.
- `--json` output and a `--check` CI gate.

[0.2.0]: https://github.com/jmweb-org/dsdiff/releases/tag/v0.2.0
[0.1.0]: https://github.com/jmweb-org/dsdiff/releases/tag/v0.1.0
