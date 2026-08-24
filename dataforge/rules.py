import re
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, field_validator
from pydantic import ValidationError as PydanticValidationError

from dataforge.exceptions import RuleParseError

FieldType = Literal["string", "integer", "float", "boolean"]


class Rule(BaseModel):
    """One validation rule, applied to one column."""

    # forbid unknown keys so typos in the rules file fail loudly
    model_config = ConfigDict(extra="forbid")

    field: str
    type: FieldType | None = None
    required: bool = False
    min: float | None = None
    max: float | None = None
    pattern: str | None = None
    allowed: list[str] | None = None

    @field_validator("pattern")
    @classmethod
    def check_pattern_compiles(cls, v: str | None) -> str | None:
        if v is not None:
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"invalid regex: {e}") from e
        return v


def load_rules(path: str) -> list[Rule]:
    """Read a YAML rules file and return it as a list of Rule objects.

    Expected shape:

        rules:
          - field: name
            type: string
            required: true

    Raises:
        RuleParseError: if the file is missing, isn't valid YAML, or
            doesn't match the expected rule schema.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            # safe_load, not load — load() can construct arbitrary Python
            # objects from the file, which is code execution if the rules
            # file came from somewhere untrusted.
            data = yaml.safe_load(f)
    except FileNotFoundError as e:
        raise RuleParseError(f"rules file not found: {path}") from e
    except yaml.YAMLError as e:
        raise RuleParseError(f"could not parse {path} as YAML: {e}") from e

    if not isinstance(data, dict) or "rules" not in data:
        raise RuleParseError(f"{path} must contain a top-level 'rules' key")

    raw_rules = data["rules"]
    if not isinstance(raw_rules, list):
        raise RuleParseError(f"'rules' in {path} must be a list")

    if not raw_rules:
        raise RuleParseError(f"{path} contains no rules")

    rules = []
    for i, raw in enumerate(raw_rules):
        try:
            rules.append(Rule.model_validate(raw))
        except PydanticValidationError as e:
            raise RuleParseError(f"rule {i} in {path} is invalid: {e}") from e

    return rules