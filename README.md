# DataForge

A command-line tool for validating CSV files using validation rules written in YAML.

I built DataForge to learn more about file parsing, validation pipelines, testing, and building Python CLI applications. Instead of hardcoding validation logic, the validation rules are defined in a YAML file, making it easy to reuse the same validation engine for different CSV datasets.

The project is still a work in progress, but the features below are already implemented and working.

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
| --- | --- |
| `field` | Column name to validate (required) |
| `type` | `string`, `integer`, `float`, or `boolean` |
| `required` | Whether the value must exist |
| `min` | Minimum numeric value |
| `max` | Maximum numeric value |
| `pattern` | Regular expression the value must match |
| `allowed` | List of allowed values |

There are three design decisions worth mentioning.

If a key is misspelled (for example, `requird`), DataForge raises an error instead of silently ignoring it. I felt it was better to fail immediately than let someone think a validation rule was running when it actually wasn't.

An empty rules file also raises an error. Reporting that a file is "valid" when no validation rules were executed didn't seem useful, so I chose to treat that as a configuration error.

For the same reason, if a rule names a column that isn't in the CSV header, DataForge refuses to run instead of validating. This one was actually a bug I found while reviewing the CLI. A missing column looked identical to a blank cell internally, so a typo like `field: naem` skipped every check and the file came back clean. A validator that quietly stops validating but still reports success is worse than one that crashes, so it now fails with exit code 2 and names the columns it couldn't find.

---

## Usage

Validate a CSV file with a rules file:

```bash
dataforge validate data.csv --rules rules.yaml
```

A sample dataset and rules file are included in the `examples/` directory:

```bash
dataforge validate examples/sample_data.csv --rules examples/sample_rules.yaml
```

The sample data intentionally contains a few validation errors, so running the command prints something like:

```text
row 2: age should be at most 120.0, got 200
row 3: name is required but missing
row 4: age should be an integer, got 'abc'

3 errors in 3 of 4 rows
```

When the file passes validation, the output is simply:

```text
4 rows checked, no errors
```

Row numbers refer only to the data rows, so row 1 is the first row below the CSV header. That's usually the row you'll look for when opening the file in Excel or another spreadsheet application.

---

## Command-line options

| Option | Description |
| --- | --- |
| `-r`, `--rules PATH` | Path to the YAML rules file (required) |
| `-f`, `--format text\|json` | Output format (`text` by default) |
| `--max-errors N` | Display only the first **N** errors while still counting every error found |
| `-q`, `--quiet` | Print nothing when validation succeeds |

Using `--format json` produces the same validation results as structured JSON, making it easier to integrate DataForge into scripts or automation.

---

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Validation completed successfully with no errors |
| `1` | Validation completed, but the data failed one or more rules |
| `2` | DataForge couldn't run because of a setup or configuration problem |

Exit codes **1** and **2** are intentionally different. Exit code **1** means the CSV data failed validation, while exit code **2** means DataForge couldn't run at all (for example, because the rules file couldn't be loaded, or because a rule referred to a column the CSV doesn't have). Keeping them separate makes it easier for scripts and CI pipelines to handle each situation appropriately.

Validation results are written to **stdout**. If DataForge can't run, the error message is written to **stderr** instead.

---

## Current state

At this point the project can:

- Load CSV files
- Parse validation rules from YAML
- Validate rows using multiple rule types
- Generate validation reports
- Output results as text or JSON
- Run from the command line

I'm still working on improving the project, but the complete validation pipeline is now functional end to end.

---

## Development

Python 3.12

```bash
conda create -n dataforge-dev python=3.12
conda activate dataforge-dev

pip install -e ".[dev]"

pytest
```