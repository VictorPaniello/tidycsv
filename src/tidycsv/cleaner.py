"""Core cleaning pipeline: load a messy file, map its columns onto the schema,
coerce and validate each field, flag duplicates, and produce a clean DataFrame
plus a structured report of everything that happened along the way."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from dateutil import parser as date_parser

from tidycsv.schema import FieldType, Schema, _normalize_header

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CURRENCY_KEEP_RE = re.compile(r"[^\d,.\-]")
PHONE_STRIP_RE = re.compile(r"[^\d+]")


@dataclass
class RowIssue:
    row_index: int
    field: str
    issue: str


@dataclass
class CleanResult:
    clean_df: pd.DataFrame
    rows_total: int
    rows_dropped_duplicates: int
    issues: list[RowIssue] = field(default_factory=list)

    def column_issue_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for issue in self.issues:
            counts[issue.field] = counts.get(issue.field, 0) + 1
        return counts

    def flagged_row_indices(self) -> set[int]:
        return {issue.row_index for issue in self.issues}


def load_input(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path, dtype=str)
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def map_columns(df: pd.DataFrame, schema: Schema) -> pd.DataFrame:
    """Rename every column whose header matches a known alias onto its canonical
    field name. Columns with no match in the schema are dropped - they're not
    part of the contract we're cleaning towards."""
    lookup = schema.alias_lookup()
    rename_map: dict[str, str] = {}
    for col in df.columns:
        canonical = lookup.get(_normalize_header(str(col)))
        if canonical:
            rename_map[col] = canonical
    mapped = df.rename(columns=rename_map)
    keep = [f.name for f in schema.fields if f.name in mapped.columns]
    return mapped[keep]


def _coerce_string(value: str) -> tuple[str | None, str | None]:
    cleaned = value.strip()
    return (cleaned or None), None


def _coerce_email(value: str) -> tuple[str | None, str | None]:
    cleaned = value.strip().lower()
    if not cleaned:
        return None, None
    if not EMAIL_RE.match(cleaned):
        return cleaned, "invalid email format"
    return cleaned, None


def _coerce_date(value: str) -> tuple[str | None, str | None]:
    cleaned = value.strip()
    if not cleaned:
        return None, None
    try:
        parsed = date_parser.parse(cleaned, dayfirst=False, fuzzy=False)
        return parsed.date().isoformat(), None
    except (ValueError, OverflowError):
        return cleaned, "unparseable date"


def _coerce_currency(value: str) -> tuple[str | None, str | None]:
    """Parse a currency string into a plain "1234.56" decimal, handling both
    US/UK-style ("1,200.50") and EU-style ("1.200,50" / "99,99") separators.

    Which character is the decimal point is genuinely ambiguous from the
    string alone when only a comma is present - "99,99" almost always means
    99.99, but "12,345" almost always means 12345. We resolve that with a
    heuristic (see inline comments) rather than silently guessing wrong the
    way a naive digit-strip would: a plain `[^\\d.-]` strip turns "99,99"
    into "9999", off by two orders of magnitude, with no error raised."""
    cleaned = value.strip()
    if not cleaned:
        return None, None

    kept = CURRENCY_KEEP_RE.sub("", cleaned)
    if not kept:
        return cleaned, "unparseable currency amount"

    last_comma = kept.rfind(",")
    last_dot = kept.rfind(".")

    if last_comma != -1 and last_dot != -1:
        # Both separators present: whichever comes last is the decimal point,
        # the other is a thousands separator ("1,200.50" vs "1.200,50").
        if last_comma > last_dot:
            normalized = kept.replace(".", "").replace(",", ".")
        else:
            normalized = kept.replace(",", "")
    elif last_comma != -1:
        # Only a comma. Currency amounts almost never carry 3+ decimal
        # digits, so exactly 2 digits after the last comma means it's a
        # decimal point ("99,99" -> 99.99); anything else means thousands
        # separator ("12,345" -> 12345, "1,234,567" -> 1234567).
        digits_after = len(kept) - last_comma - 1
        normalized = kept.replace(",", ".") if digits_after == 2 else kept.replace(",", "")
    else:
        normalized = kept

    try:
        return f"{float(normalized):.2f}", None
    except ValueError:
        return cleaned, "unparseable currency amount"


def _coerce_integer(value: str) -> tuple[str | None, str | None]:
    cleaned = value.strip()
    if not cleaned:
        return None, None
    try:
        return str(int(float(cleaned))), None
    except ValueError:
        return cleaned, "unparseable integer"


def _coerce_phone(value: str) -> tuple[str | None, str | None]:
    cleaned = value.strip()
    if not cleaned:
        return None, None
    stripped = PHONE_STRIP_RE.sub("", cleaned)
    if len(stripped.lstrip("+")) < 7:
        return stripped, "phone number too short"
    return stripped, None


_COERCERS = {
    FieldType.STRING: _coerce_string,
    FieldType.EMAIL: _coerce_email,
    FieldType.DATE: _coerce_date,
    FieldType.CURRENCY: _coerce_currency,
    FieldType.INTEGER: _coerce_integer,
    FieldType.PHONE: _coerce_phone,
}


def coerce_and_validate(df: pd.DataFrame, schema: Schema) -> tuple[pd.DataFrame, list[RowIssue]]:
    issues: list[RowIssue] = []
    out = df.copy()

    for spec in schema.fields:
        if spec.name not in out.columns:
            if spec.required:
                for idx in out.index:
                    issues.append(RowIssue(idx, spec.name, "required column missing from input"))
            continue

        coercer = _COERCERS[spec.type]
        new_values = []
        for idx, raw in out[spec.name].items():
            value, problem = coercer(str(raw) if raw is not None else "")
            if problem:
                issues.append(RowIssue(idx, spec.name, problem))
            if value is None and spec.required:
                issues.append(RowIssue(idx, spec.name, "required field is empty"))
            new_values.append(value)
        out[spec.name] = new_values

    return out, issues


def flag_duplicates(df: pd.DataFrame, key_columns: list[str]) -> tuple[pd.DataFrame, int]:
    """Drop rows that are exact duplicates on the schema's key columns, keeping
    the first occurrence. Returns the deduplicated frame and how many rows were
    dropped."""
    if not key_columns or not all(c in df.columns for c in key_columns):
        return df, 0
    before = len(df)
    deduped = df.drop_duplicates(subset=key_columns, keep="first")
    return deduped, before - len(deduped)


def clean(input_path: str | Path, schema: Schema) -> CleanResult:
    raw = load_input(input_path)
    mapped = map_columns(raw, schema)
    coerced, issues = coerce_and_validate(mapped, schema)
    deduped, dropped = flag_duplicates(coerced, schema.key_columns)

    # Issues recorded against rows that got deduplicated away no longer apply.
    surviving_issues = [i for i in issues if i.row_index in deduped.index]

    return CleanResult(
        clean_df=deduped.reset_index(drop=True),
        rows_total=len(raw),
        rows_dropped_duplicates=dropped,
        issues=surviving_issues,
    )
