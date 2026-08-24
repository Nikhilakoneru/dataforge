import json

from dataforge.report import (
    Report,
    RowError,
    build_report,
    format_json,
    format_text,
)
from dataforge.rules import Rule

RULES = [
    Rule(field="name", type="string", required=True),
    Rule(field="age", type="integer", min=0, max=120),
]


def test_build_report_on_empty_file():
    report = build_report([], RULES)
    assert report.total_rows == 0
    assert report.is_valid


def test_build_report_with_no_errors():
    rows = [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "45"}]
    report = build_report(rows, RULES)
    assert report.total_rows == 2
    assert report.errors == []
    assert report.is_valid


def test_row_numbers_are_one_based_and_skip_the_header():
    rows = [{"name": "Alice", "age": "30"}, {"name": "", "age": "30"}]
    report = build_report(rows, RULES)
    assert [error.row for error in report.errors] == [2]


def test_one_row_can_produce_several_errors():
    rows = [{"name": "", "age": "999"}]
    report = build_report(rows, RULES)
    assert report.error_count == 2
    assert report.rows_with_errors == 1


def test_rows_with_errors_counts_distinct_rows():
    rows = [
        {"name": "Alice", "age": "30"},
        {"name": "", "age": "999"},
        {"name": "", "age": "30"},
    ]
    report = build_report(rows, RULES)
    assert report.total_rows == 3
    assert report.error_count == 3
    assert report.rows_with_errors == 2
    assert not report.is_valid


def test_format_text_when_valid():
    report = Report(total_rows=10, errors=[])
    assert format_text(report) == "10 rows checked, no errors"


def test_format_text_uses_singular_for_one_row():
    report = Report(total_rows=1, errors=[])
    assert format_text(report) == "1 row checked, no errors"


def test_format_text_lists_each_error_with_its_row():
    report = Report(
        total_rows=3,
        errors=[RowError(2, "name is required but missing")],
    )
    output = format_text(report)
    assert "row 2: name is required but missing" in output
    assert "1 error in 1 of 3 rows" in output


def test_format_text_truncates_at_max_errors():
    errors = [RowError(n, f"problem {n}") for n in range(1, 6)]
    report = Report(total_rows=5, errors=errors)
    output = format_text(report, max_errors=2)
    assert "row 1: problem 1" in output
    assert "row 5: problem 5" not in output
    assert "... and 3 more errors" in output
    # the summary still describes the whole file, not just what was shown
    assert "5 errors in 5 of 5 rows" in output


def test_format_text_does_not_truncate_when_under_the_limit():
    report = Report(total_rows=2, errors=[RowError(1, "problem")])
    assert "... and" not in format_text(report, max_errors=10)


def test_format_json_is_parseable_and_complete():
    report = Report(
        total_rows=3,
        errors=[RowError(2, "name is required but missing")],
    )
    payload = json.loads(format_json(report))
    assert payload["valid"] is False
    assert payload["total_rows"] == 3
    assert payload["error_count"] == 1
    assert payload["rows_with_errors"] == 1
    assert payload["truncated"] is False
    assert payload["errors"] == [{"row": 2, "message": "name is required but missing"}]


def test_format_json_flags_truncation_but_keeps_full_counts():
    errors = [RowError(n, f"problem {n}") for n in range(1, 6)]
    payload = json.loads(format_json(Report(5, errors), max_errors=2))
    assert payload["truncated"] is True
    assert payload["error_count"] == 5
    assert len(payload["errors"]) == 2


def test_format_json_when_valid():
    payload = json.loads(format_json(Report(total_rows=4, errors=[])))
    assert payload["valid"] is True
    assert payload["errors"] == []
