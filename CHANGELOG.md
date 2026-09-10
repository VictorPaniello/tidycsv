# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); nothing has been
tagged as a release yet, so everything below is under `[Unreleased]`.

## [Unreleased]

### Added
- Initial implementation of the `tidycsv` cleaning pipeline: `load_input`
  (CSV/Excel), `map_columns` (schema-driven header alias mapping),
  `coerce_and_validate` (per-field type coercion — `string`, `email`,
  `date`, `currency`, `integer`, `phone` — with structured issue reporting),
  and `flag_duplicates` (exact-match dedup on configurable key columns).
- `tidycsv` CLI (Typer + Rich): reads a messy CSV/Excel file against a YAML
  schema, writes a cleaned CSV and a JSON report, prints a summary table.
- YAML schema format: per-field `name`, `aliases`, `type`, `required`, plus
  top-level `key_columns` for deduplication.
- Test suite (`tests/test_cleaner.py`) against a realistic messy-data
  fixture, covering alias mapping, email/date/currency coercion, duplicate
  detection, and flagged-not-dropped validation failures.
- GitHub Actions CI (lint via `ruff`, tests via `pytest`, Python 3.11 & 3.12).
- MIT license.

### Fixed
- **Silent currency-parsing bug**: `_coerce_currency` used to strip every
  non-digit character indiscriminately, so an EU-style decimal comma
  (`"99,99"`) was misread as `"9999.00"` — two orders of magnitude wrong,
  with no issue flagged. Found live while demoing the tool on an invented
  EU-flavored dataset, not from a pre-planned test case. Replaced with
  separator-inference logic (whichever of `,` / `.` appears last is the
  decimal point; a lone comma is treated as decimal only when exactly 2
  digits follow it) and covered with 7 regression cases spanning US/UK and
  EU conventions.

### Changed
- README: made explicit that `input_file` and `--schema` are required
  while `--output` / `--report` are optional (default to `clean.csv` /
  `report.json`) — matching the CLI's own `--help` output, which already
  marks them `[required]` / `[default: ...]`.
- README: documented the currency parser's separator-inference behavior
  and the genuine ambiguity that remains for it (locale can't always be
  inferred from the string alone).

### Known limitations (tracked, not yet addressed)
- No fuzzy/near-duplicate matching — only exact matches on the schema's
  key columns, after cleaning, are deduplicated.
- No custom validation rules beyond the six built-in field types.
- No streaming support — the whole input file is loaded into memory via
  pandas.
- A phone number's leading `00` international-dialing prefix is not
  normalized to `+` (inconsistent formatting, not incorrect data).
