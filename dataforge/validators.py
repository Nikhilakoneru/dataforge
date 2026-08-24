import re

from dataforge.rules import Rule

BOOL_VALUES = {"true", "false", "yes", "no", "1", "0"}


def is_empty(row: dict[str, str], field: str) -> bool:
    """A field counts as empty if the column is missing or the cell is blank."""
    return not row.get(field, "").strip()


def check_required(row: dict[str, str], rule: Rule) -> list[str]:
    if rule.required and is_empty(row, rule.field):
        return [f"{rule.field} is required but missing"]
    return []


def check_type(row: dict[str, str], rule: Rule) -> list[str]:
    if rule.type is None or is_empty(row, rule.field):
        return []

    value = row[rule.field].strip()

    if rule.type == "integer":
        try:
            int(value)
        except ValueError:
            return [f"{rule.field} should be an integer, got '{value}'"]
    elif rule.type == "float":
        try:
            float(value)
        except ValueError:
            return [f"{rule.field} should be a number, got '{value}'"]
    elif rule.type == "boolean" and value.lower() not in BOOL_VALUES:
        return [f"{rule.field} should be true/false, got '{value}'"]
    # "string" accepts anything that isn't empty

    return []
def check_range(row: dict[str, str], rule: Rule) -> list[str]:
    if (rule.min is None and rule.max is None) or is_empty(row, rule.field):
        return []

    value = row[rule.field].strip()
    try:
        number = float(value)
    except ValueError:
        # check_type already reports this if a type was declared
        if rule.type is None:
            return [f"{rule.field} should be a number to check its range, got '{value}'"]
        return []

    errors = []
    if rule.min is not None and number < rule.min:
        errors.append(f"{rule.field} should be at least {rule.min}, got {value}")
    if rule.max is not None and number > rule.max:
        errors.append(f"{rule.field} should be at most {rule.max}, got {value}")
    return errors


def check_pattern(row: dict[str, str], rule: Rule) -> list[str]:
    if rule.pattern is None or is_empty(row, rule.field):
        return []

    value = row[rule.field].strip()
    if re.search(rule.pattern, value) is None:
        return [f"{rule.field} doesn't match pattern {rule.pattern}, got '{value}'"]
    return []


def check_allowed(row: dict[str, str], rule: Rule) -> list[str]:
    if rule.allowed is None or is_empty(row, rule.field):
        return []

    value = row[rule.field].strip()
    if value not in rule.allowed:
        return [f"{rule.field} should be one of {rule.allowed}, got '{value}'"]
    return []

# Order matters: required first (a missing value makes the rest moot),
# then type, then the checks that assume a well-formed value.
VALIDATORS = [
    check_required,
    check_type,
    check_range,
    check_pattern,
    check_allowed,
]


def validate_row(row: dict[str, str], rules: list[Rule]) -> list[str]:
    """Run every validator against every rule and return all errors found."""
    errors = []
    for rule in rules:
        for validator in VALIDATORS:
            errors.extend(validator(row, rule))
    return errors