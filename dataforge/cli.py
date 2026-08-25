"""Command line entry point for DataForge.

Exit codes are the real interface here — a CI job reads those, not the
text output:

    0  every row passed
    1  the file loaded fine but the data broke the rules
    2  DataForge couldn't run at all — bad path, unreadable rules file,
       or rules naming columns the CSV doesn't have

Keeping 1 and 2 apart matters: "your data is wrong" and "your setup is
wrong" need different reactions from whoever is watching the pipeline.
"""

import logging
import sys
import time

import click

from dataforge import __version__
from dataforge.exceptions import DataForgeError
from dataforge.loaders import load_csv, read_header
from dataforge.logs import LOG_LEVELS, configure_logging, log_event
from dataforge.report import build_report, format_json, format_text
from dataforge.rules import load_rules
from dataforge.validators import missing_rule_fields

EXIT_INVALID_DATA = 1
EXIT_CANNOT_RUN = 2


class CliError(click.ClickException):
    """Something stopped DataForge before it could check any data.

    click.ClickException prints 'Error: <message>' to stderr and exits
    with exit_code, so overriding exit_code is all we need to separate
    this from a data failure.
    """

    exit_code = EXIT_CANNOT_RUN


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="dataforge")
def main() -> None:
    """Validate CSV files against rules written in YAML."""


@main.command()
@click.argument(
    "csv_path",
    metavar="CSV_FILE",
    type=click.Path(exists=True, dir_okay=False, readable=True),
)
@click.option(
    "-r",
    "--rules",
    "rules_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Path to the YAML rules file.",
)
@click.option(
    "-f",
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="How to print the results.",
)
@click.option(
    "--max-errors",
    type=click.IntRange(min=1),
    default=None,
    help="Only list the first N errors. Counts still cover the whole file.",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Print nothing when the file passes. Failures are still reported.",
)
@click.option(
    "--log-level",
    type=click.Choice(LOG_LEVELS),
    default="off",
    show_default=True,
    help="Emit JSON diagnostic logs to stderr. Separate from --format.",
)
def validate(
    csv_path: str,
    rules_path: str,
    output_format: str,
    max_errors: int | None,
    quiet: bool,
    log_level: str,
) -> None:
    """Check CSV_FILE against a rules file."""
    configure_logging(log_level)
    started = time.perf_counter()
    log_event(
        "run.started",
        csv_path=csv_path,
        rules_path=rules_path,
        output_format=output_format,
    )

    try:
        rules = load_rules(rules_path)
        log_event("rules.loaded", rule_count=len(rules))

        header = read_header(csv_path)
        rows = load_csv(csv_path)
        log_event("csv.loaded", row_count=len(rows), column_count=len(header))
    except DataForgeError as e:
        # Every failure in the loader and the parser layer means we
        # never got as far as looking at the data, so they all collapse
        # into the same "couldn't run" exit code.
        log_event(
            "run.failed",
            level=logging.ERROR,
            error_type=type(e).__name__,
            exit_code=EXIT_CANNOT_RUN,
        )
        raise CliError(str(e)) from e

    # Refuse to run rather than validate against a header that doesn't
    # have the columns the rules talk about. Those rules would skip
    # every check and the file would come back clean, which is the one
    # outcome a validator must never produce by accident.
    missing = missing_rule_fields(header, rules)
    if missing:
        # Field names come from the rules file the user wrote, not from
        # the data, so they're safe to log.
        log_event(
            "rules.header_mismatch",
            level=logging.ERROR,
            missing_fields=missing,
            exit_code=EXIT_CANNOT_RUN,
        )
        raise CliError(
            f"{rules_path} has rules for columns that are not in "
            f"{csv_path}: {', '.join(missing)}"
        )

    report = build_report(rows, rules)

    # Counts only. The error messages themselves quote the offending
    # cell values, which must not reach a log aggregator.
    log_event(
        "run.finished",
        valid=report.is_valid,
        total_rows=report.total_rows,
        error_count=report.error_count,
        rows_with_errors=report.rows_with_errors,
        duration_ms=round((time.perf_counter() - started) * 1000, 1),
        exit_code=0 if report.is_valid else EXIT_INVALID_DATA,
    )

    if not (quiet and report.is_valid):
        render = format_json if output_format == "json" else format_text
        click.echo(render(report, max_errors))

    if not report.is_valid:
        sys.exit(EXIT_INVALID_DATA)
