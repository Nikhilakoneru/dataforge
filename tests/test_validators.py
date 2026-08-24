from dataforge.rules import Rule
from dataforge.validators import check_required, check_type


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