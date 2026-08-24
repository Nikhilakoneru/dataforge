# DataForge

A Python project for validating CSV files using YAML-based validation rules.

This project is still in progress. The sections below describe the features that are currently implemented.

## Rules file

You write rules in a YAML file, one entry per column you want to check:

```yaml
rules:
  - field: name
    type: string
    required: true
  - field: age
    type: integer
    min: 0
    max: 120
```

Keys you can use: `field` (the only required one), `type` (`string`, `integer`, `float`, `boolean`), `required`, `min`, `max`, `pattern` for a regex, and `allowed` for a list of valid values.

There are two intentional decisions here.

If you misspell a key (for example, `requird`), parsing fails instead of silently ignoring it. That makes configuration mistakes easier to catch.

An empty rules file also raises an error. I decided it's better to fail than to report success when no validation rules actually ran.

## Current state

Right now it can load CSVs and parse the rules file. The validators and the CLI aren't done yet, so you can't actually run it against a file end to end.

## Development

Python 3.12.

```bash
conda create -n dataforge-dev python=3.12
conda activate dataforge-dev
pip install -e ".[dev]"
pytest
```