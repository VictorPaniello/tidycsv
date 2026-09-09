"""tidycsv command-line interface."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tidycsv.cleaner import clean
from tidycsv.report import build_report, write_report
from tidycsv.schema import Schema

app = typer.Typer(add_completion=False, help="Normalize a messy CSV/Excel export against a schema")
console = Console()

_INPUT_HELP = "Messy CSV or .xlsx file to clean."
_SCHEMA_HELP = "YAML schema file."
_OUTPUT_HELP = "Where to write the cleaned CSV."
_REPORT_HELP = "Where to write the JSON report."


@app.command(name="clean")
def clean_cmd(
    input_file: Path = typer.Argument(..., exists=True, help=_INPUT_HELP),
    schema: Path = typer.Option(..., "--schema", "-s", exists=True, help=_SCHEMA_HELP),
    output: Path = typer.Option(Path("clean.csv"), "--output", "-o", help=_OUTPUT_HELP),
    report: Path = typer.Option(Path("report.json"), "--report", "-r", help=_REPORT_HELP),
) -> None:
    """Clean INPUT_FILE against SCHEMA and write the result to --output / --report."""
    loaded_schema = Schema.load(schema)
    result = clean(input_file, loaded_schema)

    result.clean_df.to_csv(output, index=False)
    report_dict = build_report(input_file, result)
    write_report(report_dict, report)

    table = Table(title=f"tidycsv - {input_file.name}")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Rows in", str(report_dict["rows_total"]))
    table.add_row("Rows clean", str(report_dict["rows_clean"]))
    table.add_row("Rows flagged", str(report_dict["rows_flagged"]))
    table.add_row("Duplicates dropped", str(report_dict["rows_dropped_duplicates"]))
    console.print(table)

    if report_dict["column_issue_counts"]:
        issues_table = Table(title="Issues by column")
        issues_table.add_column("Column")
        issues_table.add_column("Count", justify="right")
        for col, count in sorted(report_dict["column_issue_counts"].items(), key=lambda kv: -kv[1]):
            issues_table.add_row(col, str(count))
        console.print(issues_table)

    console.print(f"\n[green]Clean file:[/green] {output}")
    console.print(f"[green]Report:[/green] {report}")


if __name__ == "__main__":
    app()
