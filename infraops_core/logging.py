"""Logging utilities configured for structured output."""

from __future__ import annotations

import logging
from typing import Any, cast

import structlog
from structlog.stdlib import BoundLogger


def configure_logging(level: int = logging.INFO) -> None:
    """Configure standard library logging and structlog for structured output."""

    timestamper = structlog.processors.TimeStamper(fmt="iso")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(level=level)


def get_logger(name: str | None = None) -> BoundLogger:
    """Return a structlog logger bound to a module or component name."""

    return cast(BoundLogger, structlog.get_logger(name))


def bind_context(**kwargs: Any) -> None:
    """Bind contextual key/value pairs to the current logging context."""

    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear the currently bound logging context."""

    structlog.contextvars.clear_contextvars()


__all__ = ["bind_context", "clear_context", "configure_logging", "get_logger"]
