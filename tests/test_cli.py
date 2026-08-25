import json

import pytest
from click.testing import CliRunner

from dataforge.cli import main

RULES = """
rules:
  - field: name
    type: string
    required: true
  - field: age
    type: integer
    min: 0
    max: 120
"""

VALID_CSV = "name,age\nAlice,30\nBob,45\n"

# three rows, one error each: age too high, name missing, age not an integer
INVALID_CSV = "name,age\nAlice,200\n,30\nCarol,abc\n"


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def rules_file(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text(RULES, encoding="utf-8")
    return str(path)


def write_csv(tmp_path, content):
    path = tmp_path / "data.csv"
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_valid_file_exits_zero(runner, tmp_path, rules_file):
    csv_path = write_csv(tmp_path, VALID_CSV)
    result = runner.invoke(main, ["validate", csv_path, "--rules", rules_file])
    assert result.exit_code == 0
    assert "2 rows checked, no errors" in result.stdout


def test_invalid_file_exits_one_and_reports_on_stdout(runner, tmp_path, rules_file):
    csv_path = write_csv(tmp_path, INVALID_CSV)
    result = runner.invoke(main, ["validate", csv_path, "--rules", rules_file])
    assert result.exit_code == 1
    assert "row 1:" in result.stdout
    assert "row 2: name is required but missing" in result.stdout
    assert "3 errors in 3 of 3 rows" in result.stdout


def test_missing_csv_exits_two(runner, tmp_path, rules_file):
    result = runner.invoke(
        main, ["validate", str(tmp_path / "nope.csv"), "--rules", rules_file]
    )
    assert result.exit_code == 2


def test_missing_rules_file_exits_two(runner, tmp_path):
    csv_path = write_csv(tmp_path, VALID_CSV)
    result = runner.invoke(
        main, ["validate", csv_path, "--rules", str(tmp_path / "nope.yaml")]
    )
    assert result.exit_code == 2


def test_broken_rules_file_exits_two_with_message_on_stderr(runner, tmp_path):
    csv_path = write_csv(tmp_path, VALID_CSV)
    rules_path = tmp_path / "bad.yaml"
    rules_path.write_text("rules: []\n", encoding="utf-8")
    result = runner.invoke(main, ["validate", csv_path, "--rules", str(rules_path)])
    assert result.exit_code == 2
    assert "no rules" in result.stderr
    assert result.stdout == ""


def test_json_format_is_machine_readable(runner, tmp_path, rules_file):
    csv_path = write_csv(tmp_path, INVALID_CSV)
    result = runner.invoke(
        main, ["validate", csv_path, "--rules", rules_file, "--format", "json"]
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["valid"] is False
    assert payload["error_count"] == 3
    assert payload["errors"][1]["row"] == 2


def test_max_errors_limits_the_listing(runner, tmp_path, rules_file):
    csv_path = write_csv(tmp_path, INVALID_CSV)
    result = runner.invoke(
        main, ["validate", csv_path, "--rules", rules_file, "--max-errors", "1"]
    )
    assert result.exit_code == 1
    assert "... and 2 more errors" in result.stdout
    assert "3 errors in 3 of 3 rows" in result.stdout


def test_max_errors_rejects_zero(runner, tmp_path, rules_file):
    csv_path = write_csv(tmp_path, INVALID_CSV)
    result = runner.invoke(
        main, ["validate", csv_path, "--rules", rules_file, "--max-errors", "0"]
    )
    assert result.exit_code == 2


def test_quiet_says_nothing_when_the_file_passes(runner, tmp_path, rules_file):
    csv_path = write_csv(tmp_path, VALID_CSV)
    result = runner.invoke(
        main, ["validate", csv_path, "--rules", rules_file, "--quiet"]
    )
    assert result.exit_code == 0
    assert result.stdout == ""


def test_quiet_still_reports_failures(runner, tmp_path, rules_file):
    csv_path = write_csv(tmp_path, INVALID_CSV)
    result = runner.invoke(
        main, ["validate", csv_path, "--rules", rules_file, "--quiet"]
    )
    assert result.exit_code == 1
    assert "row 2: name is required but missing" in result.stdout


def test_header_only_csv_passes(runner, tmp_path, rules_file):
    csv_path = write_csv(tmp_path, "name,age\n")
    result = runner.invoke(main, ["validate", csv_path, "--rules", rules_file])
    assert result.exit_code == 0
    assert "0 rows checked, no errors" in result.stdout


def test_help_lists_the_validate_command(runner):
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "validate" in result.stdout


# --- regression: a rule naming a column the CSV doesn't have -------------
# Before this was fixed, these rules skipped every check and the file was
# reported as valid with exit code 0. Reporting success for a rule that
# was never applied is the one result a validator must never produce.

TYPO_RULES = """
rules:
  - field: naem
    type: integer
    min: 0
    max: 10
"""


def test_rule_naming_an_unknown_column_does_not_report_success(runner, tmp_path):
    csv_path = write_csv(tmp_path, VALID_CSV)
    rules_path = tmp_path / "typo.yaml"
    rules_path.write_text(TYPO_RULES, encoding="utf-8")

    result = runner.invoke(main, ["validate", csv_path, "--rules", str(rules_path)])

    assert result.exit_code == 2
    assert "no errors" not in result.stdout
    assert "naem" in result.stderr


def test_unknown_column_is_reported_even_with_quiet(runner, tmp_path):
    csv_path = write_csv(tmp_path, VALID_CSV)
    rules_path = tmp_path / "typo.yaml"
    rules_path.write_text(TYPO_RULES, encoding="utf-8")

    result = runner.invoke(
        main, ["validate", csv_path, "--rules", str(rules_path), "--quiet"]
    )

    assert result.exit_code == 2
    assert "naem" in result.stderr


def test_unknown_column_message_lists_every_missing_name(runner, tmp_path):
    csv_path = write_csv(tmp_path, VALID_CSV)
    rules_path = tmp_path / "two_typos.yaml"
    rules_path.write_text("rules:\n  - field: naem\n  - field: aeg\n", encoding="utf-8")

    result = runner.invoke(main, ["validate", csv_path, "--rules", str(rules_path)])

    assert result.exit_code == 2
    assert "naem" in result.stderr
    assert "aeg" in result.stderr


def test_unknown_column_fails_in_json_mode_too(runner, tmp_path):
    csv_path = write_csv(tmp_path, VALID_CSV)
    rules_path = tmp_path / "typo.yaml"
    rules_path.write_text(TYPO_RULES, encoding="utf-8")

    result = runner.invoke(
        main,
        ["validate", csv_path, "--rules", str(rules_path), "-f", "json"],
    )

    # no JSON claiming the file is valid should reach stdout
    assert result.exit_code == 2
    assert result.stdout == ""


def test_header_only_csv_with_matching_rules_still_passes(runner, tmp_path, rules_file):
    csv_path = write_csv(tmp_path, "name,age\n")

    result = runner.invoke(main, ["validate", csv_path, "--rules", rules_file])

    assert result.exit_code == 0
    assert "0 rows checked, no errors" in result.stdout


def test_completely_empty_csv_does_not_report_success(runner, tmp_path, rules_file):
    csv_path = write_csv(tmp_path, "")

    result = runner.invoke(main, ["validate", csv_path, "--rules", rules_file])

    assert result.exit_code == 2
    assert "no errors" not in result.stdout


# --- structured logging (#14) --------------------------------------------
# These are diagnostic logs on stderr, not the --format json result on
# stdout. The two must never be confused or mixed into one stream.


def log_lines(result):
    """Parse the JSON log lines out of a CliRunner result's stderr."""
    return [
        json.loads(line)
        for line in result.stderr.strip().splitlines()
        if line.startswith("{")
    ]


def test_logging_is_off_by_default(runner, tmp_path, rules_file):
    csv_path = write_csv(tmp_path, VALID_CSV)
    result = runner.invoke(main, ["validate", csv_path, "--rules", rules_file])

    assert result.exit_code == 0
    assert result.stderr == ""


def test_log_level_info_emits_run_events(runner, tmp_path, rules_file):
    csv_path = write_csv(tmp_path, VALID_CSV)
    result = runner.invoke(
        main,
        ["validate", csv_path, "--rules", rules_file, "--log-level", "info"],
    )

    events = [entry["event"] for entry in log_lines(result)]
    assert events == [
        "run.started",
        "rules.loaded",
        "csv.loaded",
        "run.finished",
    ]


def test_run_finished_carries_counts_and_duration(runner, tmp_path, rules_file):
    csv_path = write_csv(tmp_path, INVALID_CSV)
    result = runner.invoke(
        main,
        ["validate", csv_path, "--rules", rules_file, "--log-level", "info"],
    )

    finished = log_lines(result)[-1]
    assert finished["valid"] is False
    assert finished["total_rows"] == 3
    assert finished["error_count"] == 3
    assert finished["exit_code"] == 1
    assert isinstance(finished["duration_ms"], float)


def test_logs_never_contain_cell_values(runner, tmp_path, rules_file):
    """The privacy guarantee for #14, as an executable check.

    CSV contents can be personal data and logs get shipped to places
    with far broader access than the file itself, so no cell value may
    appear in a log line — not even one that failed validation.
    """
    csv_path = write_csv(tmp_path, "name,age\nalice@example.com,999\nBobSecret,abc\n")
    result = runner.invoke(
        main,
        ["validate", csv_path, "--rules", rules_file, "--log-level", "debug"],
    )

    logs = result.stderr
    assert "alice@example.com" not in logs
    assert "BobSecret" not in logs
    assert "999" not in logs
    assert "abc" not in logs
    # ...while the user-facing report on stdout still shows them
    assert "999" in result.stdout


def test_loader_failure_is_logged_with_error_type(runner, tmp_path):
    csv_path = write_csv(tmp_path, VALID_CSV)
    rules_path = tmp_path / "bad.yaml"
    rules_path.write_text("rules: []\n", encoding="utf-8")

    result = runner.invoke(
        main,
        [
            "validate",
            csv_path,
            "--rules",
            str(rules_path),
            "--log-level",
            "info",
        ],
    )

    failed = [e for e in log_lines(result) if e["event"] == "run.failed"]
    assert failed[0]["error_type"] == "RuleParseError"
    assert failed[0]["exit_code"] == 2


def test_header_mismatch_is_logged_with_missing_fields(runner, tmp_path):
    csv_path = write_csv(tmp_path, VALID_CSV)
    rules_path = tmp_path / "typo.yaml"
    rules_path.write_text(TYPO_RULES, encoding="utf-8")

    result = runner.invoke(
        main,
        [
            "validate",
            csv_path,
            "--rules",
            str(rules_path),
            "--log-level",
            "info",
        ],
    )

    mismatch = [e for e in log_lines(result) if e["event"] == "rules.header_mismatch"]
    assert mismatch[0]["missing_fields"] == ["naem"]
    assert mismatch[0]["level"] == "error"


def test_json_output_stays_parseable_while_logging(runner, tmp_path, rules_file):
    """The reason logs go to stderr: stdout must remain valid JSON."""
    csv_path = write_csv(tmp_path, INVALID_CSV)
    result = runner.invoke(
        main,
        [
            "validate",
            csv_path,
            "--rules",
            rules_file,
            "-f",
            "json",
            "--log-level",
            "debug",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["error_count"] == 3
    assert log_lines(result)
