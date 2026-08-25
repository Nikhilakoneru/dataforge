# DataForge

DataForge is a command-line tool for validating CSV files using rules defined in a YAML file.

I built this project to learn more about file parsing, validation pipelines, testing, and designing Python command-line applications. Instead of hardcoding validation logic, the validation rules are written in a YAML file so the same validator can be reused for different CSV datasets.

At the moment, DataForge can:

- Load CSV files
- Parse validation rules from YAML
- Validate each row against those rules
- Report errors in either text or JSON format
- Run everything through a command-line interface

---

## Rules file

Validation rules are written in a YAML file, with one rule for each column you want to validate.

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

Supported keys:

| Key | Description |
|------|-------------|
| `field` | Column name to validate (required) |
| `type` | `string`, `integer`, `float`, or `boolean` |
| `required` | Whether the value must exist |
| `min` | Minimum numeric value |
| `max` | Maximum numeric value |
| `pattern` | Regular expression the value must match |
| `allowed` | List of allowed values |

A few design decisions are worth mentioning.

If a rule contains a misspelled key (for example, `requird`), parsing fails immediately instead of silently ignoring it. I felt that failing early makes configuration mistakes much easier to notice.

An empty rules file is also treated as an error. Reporting that a file is "valid" when no validation rules actually ran didn't seem useful, so DataForge refuses to continue instead.

While testing the CLI I also found another edge case: if a rule references a column that doesn't exist in the CSV, validation now stops with a clear error instead of silently skipping every check for that column.

---

## Usage

Validate a CSV file using a rules file:

```bash
dataforge validate data.csv --rules rules.yaml
```

A sample dataset and rules file are included in the `examples/` directory.

```bash
dataforge validate examples/sample_data.csv --rules examples/sample_rules.yaml
```

The sample dataset intentionally contains validation errors, so running the command prints something like:

```text
row 2: age should be at most 120.0, got 200
row 3: name is required but missing
row 4: age should be an integer, got 'abc'

3 errors in 3 of 4 rows
```

When the file passes validation:

```text
4 rows checked, no errors
```

Row numbers refer only to data rows. Row 1 is the first row after the CSV header, which makes it easier to locate the problem in spreadsheet applications like Excel.

---

## Command-line options

| Option | Description |
|------|-------------|
| `-r`, `--rules PATH` | Path to the YAML rules file (required) |
| `-f`, `--format text\|json` | Output format (default: `text`) |
| `--max-errors N` | Display only the first N errors while still counting every error found |
| `-q`, `--quiet` | Print nothing when validation succeeds |
| `--log-level LEVEL` | Print diagnostic logs to stderr |

Using JSON output:

```bash
dataforge validate data.csv --rules rules.yaml -f json
```

The validation results are written to stdout, making them easy to use from scripts or automation.

Diagnostic logs, when enabled, are written to stderr so they never interfere with JSON output.

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Validation completed successfully |
| `1` | The CSV loaded correctly, but one or more validation rules failed |
| `2` | DataForge couldn't run because of a configuration or setup problem |

Separating exit codes `1` and `2` lets scripts distinguish between invalid data and problems with the validation setup itself.

---

## Features

Current functionality includes:

- CSV loading (including UTF-8 BOM support)
- YAML rule parsing
- Six validation rules:
  - `required`
  - `type`
  - `min`
  - `max`
  - `pattern`
  - `allowed`
- Validation reports in both text and JSON
- Structured diagnostic logging
- Command-line interface
- Comprehensive unit tests

---

## Setup

DataForge requires **Python 3.12 or newer**.

Using Conda:

```bash
conda create -n dataforge-dev python=3.12
conda activate dataforge-dev
pip install -e ".[dev]"
```

Or using a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Verify the installation:

```bash
dataforge --version
```

Runtime dependencies:

- click
- pydantic
- PyYAML

Development tools include:

- pytest
- hypothesis
- ruff
- mypy
- coverage

---

## Running tests

```bash
pytest

pytest --cov=dataforge

ruff check . && ruff format --check .

mypy dataforge tests
```

The project currently contains:

- 114 unit tests
- 100% statement coverage
- mypy strict mode
- Ruff formatting and linting
- GitHub Actions CI

Some validator tests use Hypothesis to generate random test cases rather than relying only on hand-written examples.

---

## Performance

A small benchmark script is included:

```bash
python scripts/benchmark.py
```

On my laptop (Apple M5, Python 3.12), validating a CSV with 100,000 rows takes about **0.22 seconds**, which works out to roughly **460,000 rows per second**.

These numbers are only meant as a rough reference since they'll vary between machines.

At the moment, the loader reads the entire CSV into memory before validation begins, so memory usage grows with file size.

---

## Current limitations

There are still a few things I'd improve in the future.

- The whole CSV is loaded into memory before validation.
- Rules only validate one column at a time.
- One rules file validates one CSV.
- Errors are returned as text instead of structured objects.
- Numeric bounds display as `120.0` instead of `120`.
- Passing a directory reports an `IsADirectoryError`.
- Only UTF-8 input is supported.

---

## What I learned

This project taught me much more than just writing validation functions.

One lesson was that small design decisions become much more useful as a project grows. For example, I originally wasn't convinced the custom exception hierarchy was necessary, but once I built the CLI it made error handling much cleaner.

I also learned that reporting errors is just as important as finding them. Features like row numbering, exit codes, JSON output, and separate stdout/stderr streams don't change how validation works, but they make the tool much easier to use in scripts and automation.

Probably the most interesting bug I found happened while testing the CLI. If a rule referenced a column that didn't exist, validation quietly skipped every check and incorrectly reported that the file was valid. Fixing that made me appreciate how important edge cases are when building developer tools.

---

## Project structure

```
dataforge/
├── loaders.py        # Read CSV files
├── rules.py          # Parse YAML rules
├── validators.py     # Validation functions
├── report.py         # Build validation reports
├── logs.py           # Structured logging
├── cli.py            # Command-line interface
├── exceptions.py     # Custom exceptions
tests/                # Unit tests
examples/             # Sample CSV and YAML files
scripts/              # Benchmark script
```

The project follows a simple pipeline:

```
CSV + Rules
      │
      ▼
 Loaders
      │
      ▼
 Rule Parser
      │
      ▼
 Validators
      │
      ▼
 Report Builder
      │
      ▼
 CLI Output
```

Keeping each stage separate made it easier to test components independently and add new functionality without changing the rest of the pipeline.