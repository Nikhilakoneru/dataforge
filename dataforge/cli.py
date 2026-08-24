"""Command line entry point for DataForge.

Exit codes are the real interface here — a CI job reads those, not the
text output:

    0  every row passed
    1  the file loaded fine but the data broke the rules
    2  DataForge couldn't run at all (bad path, unreadable rules file)

Keeping 1 and 2 apart matters: "your data is wrong" and "your setup is
wrong" need different reactions from whoever is watching the pipeline.
"""

import sys

import click

from dataforge import __version__
from dataforge.exceptions import DataForgeError
from dataforge.loaders import load_csv
from dataforge.report import build_report, format_json, format_text
from dataforge.rules import load_rules

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
def validate(
    csv_path: str,
    rules_path: str,
    output_format: str,
    max_errors: int | None,
    quiet: bool,
) -> None:
    """Check CSV_FILE against a rules file."""
    try:
        rules = load_rules(rules_path)
        rows = load_csv(csv_path)
    except DataForgeError as e:
        # Every failure in the loader and the parser layer means we
        # never got as far as looking at the data, so they all collapse
        # into the same "couldn't run" exit code.
        raise CliError(str(e)) from e

    report = build_report(rows, rules)

    if not (quiet and report.is_valid):
        render = format_json if output_format == "json" else format_text
        click.echo(render(report, max_errors))

    if not report.is_valid:
        sys.exit(EXIT_INVALID_DATA)
