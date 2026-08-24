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
