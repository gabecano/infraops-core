"""HTTP client utilities with retry and pagination helpers."""

from __future__ import annotations

import math
from collections.abc import AsyncGenerator, Callable, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from infraops_core.config import get_settings
from infraops_core.logging import get_logger


@dataclass
class PaginationState:
    """State container for paginated API responses."""

    offset: int = 0
    limit: int = 100


def _log_retry(retry_state: RetryCallState) -> None:
    logger = get_logger(__name__)
    wait_time = retry_state.next_action.sleep if retry_state.next_action else None
    logger.warning(
        "Retrying HTTP request",
        attempt=retry_state.attempt_number,
        wait=wait_time,
        last_exc=str(retry_state.outcome.exception() if retry_state.outcome else None),
    )


def _build_retry_decorator() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    settings = get_settings()
    return retry(
        reraise=True,
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
        stop=stop_after_attempt(settings.max_retry_attempts),
        wait=wait_exponential(multiplier=settings.retry_backoff_seconds, min=0),
        after=_log_retry,
    )


def create_sync_client(**kwargs: Any) -> httpx.Client:
    """Return a configured :class:`httpx.Client` with retry defaults."""

    settings = get_settings()
    timeout = kwargs.pop("timeout", settings.default_request_timeout)
    transport = kwargs.pop("transport", httpx.HTTPTransport(retries=0))

    return httpx.Client(timeout=timeout, transport=transport, **kwargs)


@asynccontextmanager
async def get_async_client(**kwargs: Any) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Context manager yielding an :class:`httpx.AsyncClient` configured with defaults."""

    settings = get_settings()
    timeout = kwargs.pop("timeout", settings.default_request_timeout)
    transport = kwargs.pop("transport", httpx.AsyncHTTPTransport(retries=0))

    async with httpx.AsyncClient(timeout=timeout, transport=transport, **kwargs) as client:
        yield client


def iter_pages(total: int, *, page_size: int) -> Iterable[PaginationState]:
    """Yield pagination state for a total record count."""

    if page_size <= 0:
        raise ValueError("page_size must be positive")

    total_pages = math.ceil(total / page_size)
    for index in range(total_pages):
        yield PaginationState(offset=index * page_size, limit=page_size)


retryable = _build_retry_decorator()

__all__ = ["PaginationState", "create_sync_client", "get_async_client", "iter_pages", "retryable"]
