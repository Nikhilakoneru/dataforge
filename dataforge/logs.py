"""Structured JSON logging for diagnosing DataForge runs.

This is a different thing from `--format json`. That is the validation
result: it goes to stdout, it's on by default, and callers parse it as
a contract. These are execution events: they go to stderr, they're off
unless asked for, and they exist for whoever has to explain a run that
already finished.

Logs go to stderr specifically so that

    dataforge validate data.csv -f json > out.json

still writes a parseable file. A log line on stdout would corrupt the
output it was meant to help debug.

Nothing in here ever receives a cell value. The logging calls live in
the CLI, which only ever handles paths, counts and durations, while the
modules that do see row data have no logger at all. That's deliberate
rather than careful: CSV contents can be personal data, and logs are
usually shipped somewhere with much broader access than the file
itself, so the safe design is one where no code path could leak a value
even by accident.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

LOGGER_NAME = "dataforge"
LOG_LEVELS = ["off", "debug", "info", "warning", "error"]


class JsonFormatter(logging.Formatter):
    """Render one log record as a single line of JSON.

    Structured fields arrive as `extra={"fields": {...}}` rather than
    being scraped off the record, which keeps the payload explicit and
    stops unrelated LogRecord attributes leaking into the output.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            # UTC, so lines from different machines can be interleaved
            # without having to guess anyone's timezone.
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname.lower(),
            "event": record.getMessage(),
        }

        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)

        # Only the exception's type, never its message. Messages from
        # RuleParseError can quote the rules file back, and this module
        # has no way to know what's in there.
        if record.exc_info and record.exc_info[0] is not None:
            payload["error_type"] = record.exc_info[0].__name__

        return json.dumps(payload)


def get_logger() -> logging.Logger:
    """The one logger this package writes to."""
    return logging.getLogger(LOGGER_NAME)


def configure_logging(level: str) -> None:
    """Point DataForge's logger at stderr as JSON. `off` silences it.

    Safe to call more than once — existing handlers are dropped first,
    so a second call doesn't double every line. The stderr stream is
    looked up here rather than at import time so that tests (and
    anything else that redirects stderr) get the stream in force when
    the command actually runs.
    """
    logger = get_logger()
    logger.handlers.clear()
    # Don't let the root logger print a second, unstructured copy.
    logger.propagate = False

    if level == "off":
        # NullHandler keeps logging's "no handler found" warning quiet.
        logger.addHandler(logging.NullHandler())
        logger.setLevel(logging.CRITICAL + 1)
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(level.upper())


def log_event(event: str, level: int = logging.INFO, **fields: Any) -> None:
    """Emit one structured event.

    `event` is a stable dotted name (`csv.loaded`) rather than a
    sentence, so logs can be grouped and counted without matching on
    prose. Pass only counts, durations, paths and option values —
    never a value read out of the CSV.
    """
    get_logger().log(level, event, extra={"fields": fields})
