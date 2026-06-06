# dsdiff

A git-style diff between two dataset files: schema changes and column-level
distribution drift, with a CI gate.

When a dataset is regenerated, columns quietly get renamed, retyped, gain
nulls, or shift distribution, and the pipeline keeps running while the model
degrades. There is no quick "git diff for data" a reviewer can read on a pull
request. `dsdiff` is that: point it at two files and it reports what changed,
ranked by how much it should worry you.

```console
$ dsdiff diff yesterday.parquet today.parquet
severity  column      change         detail
high      income      drift          PSI 0.412
high      signup_date column_added   new column
medium    age          null_rate      null rate 0.0% -> 7.3%
low       country      cardinality    distinct values 41 -> 44
```

## Install

```console
$ pip install dsdiff
```

Reads CSV, Parquet and JSON Lines through polars. No services, no schema files
to author.

## Usage

```console
$ dsdiff diff a.csv b.csv            # human-readable table
$ dsdiff diff a.csv b.csv --json     # machine-readable findings
$ dsdiff diff a.csv b.csv --markdown # a table to paste into a PR
$ dsdiff diff a.csv b.csv --check    # exit non-zero on a high-severity change
```

### Commit a baseline

Profile a dataset once and compare future data against the saved profile,
without re-reading the original file:

```console
$ dsdiff profile reference.parquet -o baseline.json
$ dsdiff diff baseline.json new_batch.parquet --check
```

The baseline stores the bin edges, so drift on `new_batch` is measured against
exactly the same buckets as the reference.

### In CI

```yaml
- run: dsdiff diff baseline.json data/current.parquet --check
```

## What it checks

- **Schema**: columns added, removed, or retyped (all high severity).
- **Nulls**: a jump in the null rate of a shared column.
- **Cardinality**: a categorical column gaining or losing distinct values.
- **Distribution drift**: the population stability index (PSI) per column,
  numeric columns binned by quantiles and categoricals by frequency.

## Severity and the PSI scale

PSI is the standard tabular drift measure. The conventional reading is used
here: below 0.1 is **low** (no meaningful shift), 0.1 to 0.25 is **medium**,
and 0.25 or above is **high**. Schema and type changes are always high. By
default `--check` fails only on high-severity findings; pass `--fail-on medium`
to tighten the gate.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Ran; no blocking finding (or `--check` not set) |
| 1 | `--check` found a finding at or above the fail threshold |
| 2 | A file was missing or in an unsupported format |

## License

MIT. See [LICENSE](LICENSE).
