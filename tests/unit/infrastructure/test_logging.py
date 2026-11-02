import json
import logging
import sys
from io import StringIO

import pytest

from src.infrastructure.logging import configure_logging, get_logger


def _capture_json_log(level: str, json_output: bool, message: str, **kwargs: object) -> dict:
    """Configure logging, emit one log line, and return the parsed JSON output."""
    buffer = StringIO()
    configure_logging(level=level, json_output=json_output, stream=buffer)
    logger = get_logger("test")
    logger.info(message, **kwargs)
    output = buffer.getvalue().strip()
    return json.loads(output)


def test_emits_json_with_timestamp_when_json_true() -> None:
    record = _capture_json_log("INFO", True, "hello")
    assert "timestamp" in record


def test_json_log_contains_event_field() -> None:
    record = _capture_json_log("INFO", True, "hello")
    assert record["event"] == "hello"


def test_json_log_contains_level_field() -> None:
    record = _capture_json_log("INFO", True, "hello")
    assert "level" in record


def test_json_log_includes_extra_kwargs() -> None:
    record = _capture_json_log("INFO", True, "hello", foo="bar", count=42)
    assert record["foo"] == "bar"
    assert record["count"] == 42


def test_get_logger_returns_bound_logger() -> None:
    configure_logging(level="INFO", json_output=True)
    logger = get_logger("mymodule")
    assert logger is not None


def test_configure_logging_console_renderer_when_json_false() -> None:
    """json_output=False selects ConsoleRenderer (line 32). Output is NOT valid JSON."""
    buffer = StringIO()
    configure_logging(level="INFO", json_output=False, stream=buffer)
    logger = get_logger("test_console")
    logger.info("console-test-event")
    output = buffer.getvalue().strip()
    # Console output is not JSON — json.loads must fail.
    with pytest.raises(Exception):
        json.loads(output)
    # But the event string must appear somewhere in the output.
    assert "console-test-event" in output
