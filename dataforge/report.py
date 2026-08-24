"""Turn raw validator output into a result a human or a CI job can read.

The validators return bare strings with no idea which row they came
from. This module runs them across every row, attaches row numbers,
and renders the outcome as text or JSON.
"""

import json
from dataclasses import dataclass

from dataforge.rules import Rule
from dataforge.validators import validate_row


@dataclass(frozen=True)
class RowError:
    """One validation failure, tied to the data row that caused it.

    `row` is 1-based and counts data rows only, so row 1 is the first
    row after the header. That's the number a person scanning the file
    is actually looking for.
    """

    row: int
    message: str


@dataclass
class Report:
    """The outcome of validating a whole file."""

    total_rows: int
    errors: list[RowError]

    @property
    def is_valid(self) -> bool:
        return not self.errors

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def rows_with_errors(self) -> int:
        """How many distinct rows failed — one row can break several rules."""
        return len({error.row for error in self.errors})


def build_report(rows: list[dict[str, str]], rules: list[Rule]) -> Report:
    """Validate every row against every rule and collect the results."""
    errors = []
    for number, row in enumerate(rows, start=1):
        for message in validate_row(row, rules):
            errors.append(RowError(row=number, message=message))
    return Report(total_rows=len(rows), errors=errors)


def _count(number: int, noun: str) -> str:
    """'1 error' / '3 errors' — avoids printing '1 errors'."""
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def _truncate(
    errors: list[RowError], max_errors: int | None
) -> tuple[list[RowError], int]:
    """Return the errors to show plus how many were held back."""
    if max_errors is None or max_errors < 1 or len(errors) <= max_errors:
        return errors, 0
    return errors[:max_errors], len(errors) - max_errors


def format_text(report: Report, max_errors: int | None = None) -> str:
    """Render a report as plain text, one error per line."""
    if report.is_valid:
        return f"{_count(report.total_rows, 'row')} checked, no errors"

    shown, hidden = _truncate(report.errors, max_errors)
    lines = [f"row {error.row}: {error.message}" for error in shown]
    if hidden:
        lines.append(f"... and {_count(hidden, 'more error')}")

    summary = (
        f"{_count(report.error_count, 'error')} in {report.rows_with_errors} "
        f"of {_count(report.total_rows, 'row')}"
    )
    return "\n".join([*lines, "", summary])


def format_json(report: Report, max_errors: int | None = None) -> str:
    """Render a report as JSON, for scripts and CI jobs.

    The counts always describe the whole file even when the error list
    has been truncated, so a consumer never under-reports the damage.
    """
    shown, hidden = _truncate(report.errors, max_errors)
    payload = {
        "valid": report.is_valid,
        "total_rows": report.total_rows,
        "error_count": report.error_count,
        "rows_with_errors": report.rows_with_errors,
        "truncated": hidden > 0,
        "errors": [{"row": error.row, "message": error.message} for error in shown],
    }
    return json.dumps(payload, indent=2)
