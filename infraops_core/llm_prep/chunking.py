"""Chunking utilities for LLM preparation."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Iterator


def chunk(records: Iterable[str], *, size: int) -> Iterator[list[str]]:
    """Yield chunks of records with the requested size."""

    if size <= 0:
        raise ValueError("size must be positive")

    bucket: list[str] = []
    for record in records:
        bucket.append(record)
        if len(bucket) == size:
            yield bucket
            bucket = []
    if bucket:
        yield bucket


__all__ = ["chunk"]
