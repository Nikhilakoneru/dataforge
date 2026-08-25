from hypothesis import given
from hypothesis import strategies as st

from dataforge.rules import Rule
from dataforge.validators import (
    VALIDATORS,
    check_allowed,
    check_pattern,
    check_range,
    check_required,
    check_type,
    missing_rule_fields,
    validate_row,
)


def test_required_passes_when_value_present():
    rule = Rule(field="name", required=True)
    assert check_required({"name": "Alice"}, rule) == []


def test_required_fails_when_value_blank():
    rule = Rule(field="name", required=True)
    assert len(check_required({"name": "   "}, rule)) == 1


def test_required_fails_when_column_missing():
    rule = Rule(field="name", required=True)
    assert len(check_required({}, rule)) == 1


def test_not_required_allows_blank():
    rule = Rule(field="name", required=False)
    assert check_required({"name": ""}, rule) == []


def test_type_integer_accepts_valid():
    rule = Rule(field="age", type="integer")
    assert check_type({"age": "30"}, rule) == []


def test_type_integer_rejects_decimal():
    rule = Rule(field="age", type="integer")
    assert len(check_type({"age": "30.5"}, rule)) == 1


def test_type_integer_rejects_text():
    rule = Rule(field="age", type="integer")
    assert len(check_type({"age": "thirty"}, rule)) == 1


def test_type_float_accepts_integer_string():
    rule = Rule(field="score", type="float")
    assert check_type({"score": "10"}, rule) == []


def test_type_boolean_is_case_insensitive():
    rule = Rule(field="active", type="boolean")
    assert check_type({"active": "TRUE"}, rule) == []


def test_type_boolean_rejects_other_words():
    rule = Rule(field="active", type="boolean")
    assert len(check_type({"active": "maybe"}, rule)) == 1


def test_type_string_accepts_anything():
    rule = Rule(field="name", type="string")
    assert check_type({"name": "123"}, rule) == []


def test_type_skips_empty_value():
    rule = Rule(field="age", type="integer")
    assert check_type({"age": ""}, rule) == []


def test_type_skipped_when_no_type_specified():
    rule = Rule(field="age")
    assert check_type({"age": "whatever"}, rule) == []


def test_range_passes_within_bounds():
    rule = Rule(field="age", type="integer", min=0, max=120)
    assert check_range({"age": "50"}, rule) == []


def test_range_fails_below_min():
    rule = Rule(field="age", type="integer", min=18)
    assert len(check_range({"age": "10"}, rule)) == 1


def test_range_fails_above_max():
    rule = Rule(field="age", type="integer", max=120)
    assert len(check_range({"age": "200"}, rule)) == 1


def test_range_reports_both_bounds_separately():
    rule = Rule(field="age", min=10, max=20)
    assert len(check_range({"age": "5"}, rule)) == 1


def test_range_skips_when_no_bounds():
    rule = Rule(field="age", type="integer")
    assert check_range({"age": "999"}, rule) == []


def test_range_skips_non_numeric_when_type_declared():
    rule = Rule(field="age", type="integer", min=0)
    assert check_range({"age": "abc"}, rule) == []


def test_range_reports_non_numeric_when_no_type_declared():
    rule = Rule(field="age", min=0)
    assert len(check_range({"age": "abc"}, rule)) == 1


def test_pattern_passes_on_match():
    rule = Rule(field="code", pattern=r"^[A-Z]{3}$")
    assert check_pattern({"code": "ABC"}, rule) == []


def test_pattern_fails_on_mismatch():
    rule = Rule(field="code", pattern=r"^[A-Z]{3}$")
    assert len(check_pattern({"code": "abc1"}, rule)) == 1


def test_pattern_skips_when_not_set():
    rule = Rule(field="code")
    assert check_pattern({"code": "anything"}, rule) == []


def test_allowed_passes_for_listed_value():
    rule = Rule(field="status", allowed=["active", "inactive"])
    assert check_allowed({"status": "active"}, rule) == []


def test_allowed_fails_for_unlisted_value():
    rule = Rule(field="status", allowed=["active", "inactive"])
    assert len(check_allowed({"status": "pending"}, rule)) == 1


def test_allowed_is_case_sensitive():
    rule = Rule(field="status", allowed=["active"])
    assert len(check_allowed({"status": "ACTIVE"}, rule)) == 1


@given(st.integers(min_value=0, max_value=120))
def test_any_integer_within_bounds_passes_range(value):
    rule = Rule(field="age", type="integer", min=0, max=120)
    assert check_range({"age": str(value)}, rule) == []


@given(st.integers(min_value=121, max_value=10000))
def test_any_integer_above_max_fails_range(value):
    rule = Rule(field="age", type="integer", max=120)
    assert len(check_range({"age": str(value)}, rule)) == 1


@given(st.sampled_from(["active", "inactive", "pending"]))
def test_any_listed_value_passes_allowed(value):
    rule = Rule(field="status", allowed=["active", "inactive", "pending"])
    assert check_allowed({"status": value}, rule) == []


@given(st.integers())
def test_integers_always_pass_integer_type_check(value):
    rule = Rule(field="n", type="integer")
    assert check_type({"n": str(value)}, rule) == []


def test_validate_row_returns_no_errors_for_valid_row():
    rules = [
        Rule(field="name", type="string", required=True),
        Rule(field="age", type="integer", min=0, max=120),
    ]
    row = {"name": "Alice", "age": "30"}
    assert validate_row(row, rules) == []


def test_validate_row_collects_errors_across_rules():
    rules = [
        Rule(field="name", required=True),
        Rule(field="age", type="integer"),
    ]
    row = {"name": "", "age": "abc"}
    assert len(validate_row(row, rules)) == 2


def test_validate_row_collects_multiple_errors_for_one_field():
    rules = [Rule(field="age", min=50, max=10)]
    row = {"age": "30"}
    assert len(validate_row(row, rules)) == 2


def test_validate_row_with_no_rules_returns_no_errors():
    assert validate_row({"anything": "here"}, []) == []


def test_adding_a_validator_requires_only_registry_change():
    # If this list grows, only VALIDATORS should have needed editing.
    assert len(VALIDATORS) == 5


def test_missing_rule_fields_returns_nothing_when_all_present():
    rules = [Rule(field="name"), Rule(field="age")]

    assert missing_rule_fields(["name", "age"], rules) == []


def test_missing_rule_fields_ignores_extra_csv_columns():
    rules = [Rule(field="name")]

    assert missing_rule_fields(["name", "age", "city"], rules) == []


def test_missing_rule_fields_finds_a_typo():
    rules = [Rule(field="naem", type="integer")]

    assert missing_rule_fields(["name", "age"], rules) == ["naem"]


def test_missing_rule_fields_reports_all_of_them_in_rule_order():
    rules = [Rule(field="zzz"), Rule(field="name"), Rule(field="aaa")]

    assert missing_rule_fields(["name"], rules) == ["zzz", "aaa"]


def test_missing_rule_fields_does_not_repeat_a_name():
    rules = [Rule(field="naem", type="string"), Rule(field="naem", min=0)]

    assert missing_rule_fields(["name"], rules) == ["naem"]


def test_missing_rule_fields_treats_empty_header_as_everything_missing():
    rules = [Rule(field="name"), Rule(field="age")]

    assert missing_rule_fields([], rules) == ["name", "age"]


def test_float_type_rejects_non_numeric_value():
    rule = Rule(field="score", type="float")
    errors = check_type({"score": "high"}, rule)

    assert errors == ["score should be a number, got 'high'"]


def test_float_type_accepts_a_decimal():
    rule = Rule(field="score", type="float")
    assert check_type({"score": "3.5"}, rule) == []


def test_float_type_accepts_an_integer_string():
    rule = Rule(field="score", type="float")
    assert check_type({"score": "3"}, rule) == []
