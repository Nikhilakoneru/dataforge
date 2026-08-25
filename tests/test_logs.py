import json
import logging

import pytest

from dataforge.logs import (
    LOGGER_NAME,
    JsonFormatter,
    configure_logging,
    get_logger,
    log_event,
)


@pytest.fixture(autouse=True)
def reset_logger():
    """Leave the shared logger clean, so tests can't affect each other."""
    yield
    logger = get_logger()
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
    logger.propagate = True


def make_record(**kwargs):
    record = logging.LogRecord(
        name=LOGGER_NAME,
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=kwargs.pop("msg", "run.started"),
        args=(),
        exc_info=kwargs.pop("exc_info", None),
    )
    for key, value in kwargs.items():
        setattr(record, key, value)
    return record


def test_formatter_emits_one_json_object_per_record():
    output = JsonFormatter().format(make_record())
    payload = json.loads(output)

    assert "\n" not in output
    assert payload["event"] == "run.started"
    assert payload["level"] == "info"
    assert "timestamp" in payload


def test_formatter_timestamp_is_utc():
    payload = json.loads(JsonFormatter().format(make_record()))
    assert payload["timestamp"].endswith("+00:00")


def test_formatter_merges_structured_fields():
    record = make_record(fields={"row_count": 100, "valid": True})
    payload = json.loads(JsonFormatter().format(record))

    assert payload["row_count"] == 100
    assert payload["valid"] is True


def test_formatter_ignores_non_dict_fields():
    payload = json.loads(JsonFormatter().format(make_record(fields="nope")))
    assert payload["event"] == "run.started"


def test_formatter_records_exception_type_but_not_its_message():
    try:
        raise ValueError("secret cell value: alice@example.com")
    except ValueError:
        import sys

        record = make_record(exc_info=sys.exc_info())

    output = JsonFormatter().format(record)

    assert json.loads(output)["error_type"] == "ValueError"
    assert "alice@example.com" not in output


def test_off_produces_no_output(capsys):
    configure_logging("off")
    log_event("run.started", csv_path="data.csv")

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == ""


def test_logs_go_to_stderr_not_stdout(capsys):
    configure_logging("info")
    log_event("run.started", csv_path="data.csv")

    captured = capsys.readouterr()
    # stdout is reserved for validation results
    assert captured.out == ""
    assert json.loads(captured.err.strip())["event"] == "run.started"


def test_level_filters_lower_severity(capsys):
    configure_logging("error")
    log_event("csv.loaded", row_count=5)
    log_event("run.failed", level=logging.ERROR, error_type="LoaderError")

    lines = capsys.readouterr().err.strip().splitlines()
    events = [json.loads(line)["event"] for line in lines]
    assert events == ["run.failed"]


def test_configure_logging_is_idempotent(capsys):
    configure_logging("info")
    configure_logging("info")
    log_event("run.started")

    # a second call must not double every line
    assert len(capsys.readouterr().err.strip().splitlines()) == 1


def test_logger_does_not_propagate_to_root(capsys):
    configure_logging("info")
    assert get_logger().propagate is False
