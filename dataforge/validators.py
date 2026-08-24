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