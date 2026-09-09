"""Turn a CleanResult into the JSON report handed back to the user: what was
fixed, what was flagged, and where to look."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tidycsv.cleaner import CleanResult


def build_report(input_path: str | Path, result: CleanResult) -> dict[str, Any]:
    return {
        "input_file": str(input_path),
        "rows_total": result.rows_total,
        "rows_clean": len(result.clean_df) - len(result.flagged_row_indices()),
        "rows_flagged": len(result.flagged_row_indices()),
        "rows_dropped_duplicates": result.rows_dropped_duplicates,
        "column_issue_counts": result.column_issue_counts(),
        "flagged_rows": [
            {"row_index": issue.row_index, "field": issue.field, "issue": issue.issue}
            for issue in result.issues
        ],
    }


def write_report(report: dict[str, Any], path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
