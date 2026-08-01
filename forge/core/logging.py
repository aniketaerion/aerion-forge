"""Console, daily-file, structured, and timing-aware logging."""

import json
import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any

from rich.logging import RichHandler


class JsonFormatter(logging.Formatter):
    """Format log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        context = getattr(record, "context", None)
        if isinstance(context, dict):
            payload["context"] = context
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class LoggingManager:
    """Configure isolated application logging without global implicit state."""

    def __init__(self, logs_path: Path, level: str = "INFO") -> None:
        self.logs_path = logs_path
        self.level = getattr(logging, level.upper())

    def configure(self, logger_name: str = "forge") -> logging.Logger:
        """Return a configured logger with console and daily JSON output."""
        self.logs_path.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger(logger_name)
        logger.setLevel(self.level)
        logger.propagate = False
        logger.handlers.clear()

        console = RichHandler(rich_tracebacks=True, show_path=False, markup=False)
        console.setLevel(self.level)
        console.setFormatter(logging.Formatter("%(message)s"))

        file_handler = TimedRotatingFileHandler(
            self.logs_path / "forge.log",
            when="midnight",
            backupCount=30,
            encoding="utf-8",
            utc=True,
        )
        file_handler.setLevel(self.level)
        file_handler.setFormatter(JsonFormatter())
        file_handler.suffix = "%Y-%m-%d"
        logger.addHandler(console)
        logger.addHandler(file_handler)
        return logger


@contextmanager
def timed_operation(logger: logging.Logger, operation: str, **context: Any) -> Iterator[None]:
    """Log duration and failure metadata for a block of work."""
    started = time.perf_counter()
    logger.info("Started %s", operation, extra={"context": context})
    try:
        yield
    except Exception:
        elapsed = round(time.perf_counter() - started, 6)
        logger.exception("Failed %s after %.3fs", operation, elapsed, extra={"context": context})
        raise
    elapsed = round(time.perf_counter() - started, 6)
    logger.info(
        "Completed %s in %.3fs",
        operation,
        elapsed,
        extra={"context": {**context, "duration_seconds": elapsed}},
    )
