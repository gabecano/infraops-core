"""Veeam API client."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import httpx

from infraops_core.auth import APIKeyAuth
from infraops_core.clients.base import ChangeSource
from infraops_core.models.change_event import ChangeEvent


class VeeamClient(ChangeSource):
    """Placeholder Veeam client that satisfies the change source protocol."""

    def __init__(self, *, api_key: str, base_url: str) -> None:
        self._client = httpx.Client(base_url=base_url)
        self._auth = APIKeyAuth(header="X-RestSvcSessionId", value=api_key)

    def list_changes(
        self, **filters: Any
    ) -> Iterable[ChangeEvent]:  # pragma: no cover - roadmap placeholder
        raise NotImplementedError("Veeam change ingestion is not implemented yet")


__all__ = ["VeeamClient"]
