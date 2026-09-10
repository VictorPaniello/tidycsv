from pathlib import Path

import pytest

from tidycsv.cleaner import _coerce_currency, clean
from tidycsv.schema import Schema

FIXTURES = Path(__file__).parent.parent / "examples"


@pytest.fixture
def schema() -> Schema:
    return Schema.load(FIXTURES / "schema.example.yaml")


@pytest.fixture
def result(schema: Schema):
    return clean(FIXTURES / "messy_client_export.csv", schema)


def test_column_aliases_are_mapped_to_canonical_names(result):
    assert list(result.clean_df.columns) == ["full_name", "email", "signup_date", "amount", "phone"]


def test_emails_are_lowercased_and_trimmed(result):
    assert "john@example.com" in result.clean_df["email"].values
    assert "maria@example.com" in result.clean_df["email"].values


def test_duplicate_emails_are_deduplicated_after_normalization(result):
    # "JOHN@Example.com " and "john@example.com" are the same person once normalized.
    assert result.rows_dropped_duplicates == 1
    assert (result.clean_df["email"] == "john@example.com").sum() == 1


def test_dates_are_normalized_to_iso8601(result):
    row = result.clean_df.loc[result.clean_df["email"] == "maria@example.com"].iloc[0]
    assert row["signup_date"] == "2024-01-05"


def test_currency_amounts_are_cleaned_to_plain_numbers(result):
    # The first occurrence of john@example.com (by file order) survives deduplication.
    row = result.clean_df.loc[result.clean_df["email"] == "john@example.com"].iloc[0]
    assert row["amount"] == "1200.50"
    row2 = result.clean_df.loc[result.clean_df["email"] == "maria@example.com"].iloc[0]
    assert row2["amount"] == "980.00"


def test_invalid_email_is_flagged_not_silently_dropped(result):
    issues_for_invalid = [i for i in result.issues if i.issue == "invalid email format"]
    assert len(issues_for_invalid) == 1


def test_missing_required_field_is_flagged(result):
    required_issues = [i for i in result.issues if i.issue == "required field is empty"]
    assert any(i.field == "full_name" for i in required_issues)


def test_unparseable_date_is_flagged_and_original_value_kept(result):
    row = result.clean_df.loc[result.clean_df["email"] == "anna@example.com"].iloc[0]
    assert row["signup_date"] == "not a date"
    date_issues = [
        i for i in result.issues if i.field == "signup_date" and i.issue == "unparseable date"
    ]
    assert len(date_issues) == 1


# Regression coverage for a real bug found while live-demoing the tool: a naive
# digit-strip on "99,99" (EU decimal comma) silently produced "9999.00" - two
# orders of magnitude wrong, with no issue flagged. _coerce_currency now infers
# which separator is the decimal point instead of stripping commas blindly.
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("99,99", "99.99"),  # EU decimal comma - the bug that was found live
        ("1,200.50", "1200.50"),  # US/UK: comma=thousands, dot=decimal
        ("1.200,50", "1200.50"),  # EU: dot=thousands, comma=decimal
        ("12,345", "12345.00"),  # comma-only, 3+ trailing digits -> thousands
        ("1,234,567", "1234567.00"),  # multiple thousands separators
        ("€980", "980.00"),  # currency symbol, no separators
        ("$1,200.50", "1200.50"),  # currency symbol + thousands separator
    ],
)
def test_coerce_currency_handles_us_and_eu_separator_conventions(raw, expected):
    value, issue = _coerce_currency(raw)
    assert value == expected
    assert issue is None
