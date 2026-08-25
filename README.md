# DataForge

A command-line tool for validating CSV files using validation rules written in YAML.

I built DataForge to learn more about file parsing, validation pipelines, testing, and building Python CLI applications. Instead of hardcoding validation logic, the validation rules are defined in a YAML file, making it easy to reuse the same validation engine for different CSV datasets.

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
| `--log-level LEVEL` | Emit JSON diagnostic logs to stderr (`off` by default) |

Using `--format json` produces the same validation results as structured JSON, making it easier to integrate DataForge into scripts or automation.

`--log-level` is a separate thing from `--format json`, and it took me a moment to be clear about why. `--format json` is the *result* — it goes to stdout and it's what a calling script reads. `--log-level` produces *diagnostic logs* about the run itself (which files were opened, how many rules loaded, how long validation took), and those go to stderr and are off unless you ask for them.

Keeping them on different streams is what makes this work:

```bash
dataforge validate data.csv -r rules.yaml -f json --log-level info > results.json
```

`results.json` is still valid JSON, because the log lines went to stderr instead of being mixed into it.

The logs deliberately contain only counts, durations, file paths and field names — never a value read out of the CSV. Logs usually end up somewhere with much wider access than the data file itself, so a validator that logged cell contents would quietly turn a private CSV into a widely readable one. There's a test that checks this.

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

## What's implemented

- Load CSV files (UTF-8, with or without a BOM)
- Parse validation rules from YAML
- Six rule types: `type`, `required`, `min`, `max`, `pattern`, `allowed`
- Row-by-row validation with a report of every failure
- Output as human-readable text or JSON
- Structured JSON logs on stderr for debugging a run
- Exit codes that distinguish invalid data from a broken setup

The validation pipeline works end to end. What's *not* there is listed under [current limitations](#current-limitations) further down.

---

## Setup

DataForge needs **Python 3.12 or newer**. This matters more than it sounds: the `python3` that ships with macOS is 3.9, and installing with it fails immediately, so create an environment with an explicit version rather than relying on the system interpreter.

With conda:

```bash
conda create -n dataforge-dev python=3.12
conda activate dataforge-dev
pip install -e ".[dev]"
```

Or with venv, pointing at a 3.12 interpreter you already have:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Either way, `pip install -e ".[dev]"` installs the package plus the test and lint tools. After that `dataforge` is on your PATH:

```bash
dataforge --version
```

Runtime dependencies are `click`, `pydantic` and `pyyaml`. Everything else — pytest, hypothesis, ruff, mypy, coverage — is dev-only.

---

## Testing

```bash
pytest                                    # the suite
pytest --cov=dataforge                    # with coverage
ruff check . && ruff format --check .      # lint and formatting
mypy dataforge tests                      # type checking
```

The suite is 114 tests and currently covers 100% of the package. Coverage is configured to fail below 90%, which leaves a little room for a genuinely awkward branch without letting it quietly slide.

Some of the validator tests use [Hypothesis](https://hypothesis.readthedocs.io/) to generate inputs instead of listing them by hand — useful for checks like "every integer should pass the integer type rule", where I'd otherwise be guessing which values to try.

All four checks run on GitHub Actions for every push and pull request (`.github/workflows/ci.yml`). CI installs from `pyproject.toml` exactly the way the instructions above do, so a green build means a clean clone works and not just my laptop.

---

## Performance

There's a benchmark script that generates a large CSV from a fixed random seed and times the load-plus-validate path:

```bash
python scripts/benchmark.py              # 100,000 rows by default
python scripts/benchmark.py --rows 500000
```

On my machine — Apple M5, macOS 26.5, Python 3.12.13 — 100,000 rows across 5 rules takes a little over **0.2 seconds, so roughly 460,000 rows/second**, on a 4.8 MB input where about 10% of rows are invalid. Repeated runs land between 0.21 and 0.22 s, which is why I'd round it rather than quote a precise figure.

That number is from this specific script on this specific laptop, so treat it as a rough sense of scale rather than a benchmark result that means anything on your hardware. The seed is fixed so repeated runs are comparable, and the script reports the fastest of three runs, because a slower run usually means something else was using the CPU.

Worth being clear about the main limitation behind it: `load_csv` reads the entire file into a list of dicts before validating anything, so peak memory scales with file size. It's fine for the file sizes I had in mind, but it is not a streaming implementation.

---

## Current limitations

Things I know are missing or rough, written down rather than hidden:

- **The whole file is loaded into memory.** No streaming, so a file much larger than available RAM won't work.
- **Rules apply to single cells.** There's no way to express a relationship between two columns, like "`end_date` must be after `start_date`".
- **One rules file, one CSV per run.** No globbing or directory mode.
- **Errors report the row and a message, not a structured field/rule pair.** Fine for reading, less convenient for a script that wants to branch on the rule that failed.
- **Numeric bounds display as floats.** `max: 120` prints as `120.0`, because `min`/`max` are typed as floats internally. Cosmetic, and tracked as an issue.
- **Passing a directory instead of a file** raises `IsADirectoryError` rather than a clean `LoaderError`.
- **Only UTF-8 input.** A BOM is handled (Excel writes one), but other encodings aren't.

---

## Notes on the build

A few things I'd point at if someone asked what I actually learned here.

The exception hierarchy in `exceptions.py` looked pointless when I wrote it — four empty classes. It paid off in the CLI, where a single `except DataForgeError` handles every loader and parser failure, including ones I haven't written yet.

Truncation via `--max-errors` lives in the formatter, not in report building, so the counts always describe the whole file even when the list shown is shorter. There's a test that exists specifically to stop someone "optimising" that by truncating earlier.

The bug I'm most glad I caught was a rule naming a column that didn't exist. It silently skipped every check and reported the file as valid — a validator quietly not validating while still saying "no errors" is worse than one that crashes.

---

## Project layout

```
dataforge/
  loaders.py      read CSV files
  rules.py        parse and validate the YAML rules file
  validators.py   the individual checks, plus the registry
  report.py       collect results, format as text or JSON
  logs.py         structured JSON logging
  cli.py          command line entry point
  exceptions.py   error hierarchy
tests/            one test module per source module
examples/         sample CSV and rules file
scripts/          benchmark
```

The data flows in one direction: CSV and rules go in through the loader and parser, the validators check each row, the report collects what they found, and the CLI decides what to print and which exit code to use. Nothing in the lower layers imports the CLI, so the whole pipeline can be used as a library without it.