"""Client protocol definitions shared across integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Protocol

from infraops_core.models.change_event import ChangeEvent


class ChangeSource(Protocol):
    """Protocol describing change management systems."""

    def list_changes(self, **filters: object) -> Iterable[ChangeEvent]:
        """Return an iterable of :class:`ChangeEvent` instances."""


class PaginatedClient(ABC):
    """Abstract base class for clients supporting pagination."""

    @abstractmethod
    def _list_paginated(self, **filters: object) -> Iterable[ChangeEvent]:
        """Implementation hook that yields change events across all pages."""

    def list_changes(self, **filters: object) -> Iterable[ChangeEvent]:
        return self._list_paginated(**filters)


__all__ = ["ChangeSource", "PaginatedClient"]
