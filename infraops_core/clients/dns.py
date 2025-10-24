"""DNS provider client stubs."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from infraops_core.clients.base import ChangeSource
from infraops_core.models.change_event import ChangeEvent


class DNSClient(ChangeSource):
    """Interface for DNS change log providers."""

    def list_changes(
        self, **filters: Any
    ) -> Iterable[ChangeEvent]:  # pragma: no cover - interface stub
        return []


__all__ = ["DNSClient"]
