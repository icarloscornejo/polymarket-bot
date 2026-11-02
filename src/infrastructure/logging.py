import logging
import sys
from typing import IO, Any

import structlog


def configure_logging(
    level: str = "INFO",
    json_output: bool = True,
    stream: IO[str] | None = None,
) -> None:
    """Configure structlog with JSON or console rendering.

    Args:
        level: Standard logging level string (INFO, DEBUG, WARNING, ERROR).
        json_output: If True, emit newline-delimited JSON. Otherwise use colored console output.
        stream: Output stream. Defaults to sys.stdout.
    """
    output_stream = stream if stream is not None else sys.stdout

    shared_processors: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_output:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=output_stream),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Return a bound structlog logger for the given module name."""
    return structlog.get_logger(name)
