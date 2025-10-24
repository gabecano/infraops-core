"""Composable ETL pipeline building blocks."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
U = TypeVar("U")


@dataclass(slots=True)
class Pipeline(Generic[T, U]):
    """Simple ETL pipeline composed of normalization, validation, and serialization stages."""

    normalizer: Callable[[T], U]
    validator: Callable[[U], None]
    serializer: Callable[[Iterable[U]], Iterator[bytes]]

    def run(self, records: Iterable[T]) -> Iterator[bytes]:
        normalized = (self.normalizer(record) for record in records)
        for item in normalized:
            self.validator(item)
            yield from self.serializer([item])


__all__ = ["Pipeline"]
