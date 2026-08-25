import pytest

from dataforge.exceptions import RuleParseError
from dataforge.rules import load_rules

VALID_RULES = """
rules:
  - field: name
    type: string
    required: true
  - field: age
    type: integer
    min: 0
    max: 120
"""


def write_rules(tmp_path, content):
    path = tmp_path / "rules.yaml"
    path.write_text(content)
    return str(path)


def test_load_rules_parses_valid_file(tmp_path):
    rules = load_rules(write_rules(tmp_path, VALID_RULES))

    assert len(rules) == 2
    assert rules[0].field == "name"
    assert rules[0].required is True
    assert rules[1].min == 0
    assert rules[1].max == 120


def test_load_rules_applies_defaults(tmp_path):
    rules = load_rules(write_rules(tmp_path, "rules:\n  - field: name\n"))

    assert rules[0].required is False
    assert rules[0].type is None


def test_load_rules_missing_file_raises(tmp_path):
    with pytest.raises(RuleParseError):
        load_rules(str(tmp_path / "nope.yaml"))


def test_load_rules_malformed_yaml_raises(tmp_path):
    with pytest.raises(RuleParseError):
        load_rules(write_rules(tmp_path, "rules:\n  - field: name\n   bad: indent\n"))


def test_load_rules_missing_rules_key_raises(tmp_path):
    with pytest.raises(RuleParseError):
        load_rules(write_rules(tmp_path, "something_else: 1\n"))


def test_load_rules_empty_list_raises(tmp_path):
    with pytest.raises(RuleParseError):
        load_rules(write_rules(tmp_path, "rules: []\n"))


def test_load_rules_missing_field_key_raises(tmp_path):
    with pytest.raises(RuleParseError):
        load_rules(write_rules(tmp_path, "rules:\n  - type: string\n"))


def test_load_rules_unknown_key_raises(tmp_path):
    with pytest.raises(RuleParseError):
        load_rules(
            write_rules(tmp_path, "rules:\n  - field: name\n    requird: true\n")
        )


def test_load_rules_bad_regex_raises(tmp_path):
    with pytest.raises(RuleParseError):
        load_rules(write_rules(tmp_path, "rules:\n  - field: name\n    pattern: '['\n"))


def test_rules_key_that_is_not_a_list_raises(tmp_path):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text("rules: just-a-string\n")

    with pytest.raises(RuleParseError):
        load_rules(str(rules_file))
