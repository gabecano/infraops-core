"""Cisco Meraki API client wrapper."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import httpx

from infraops_core.auth import APIKeyAuth
from infraops_core.clients.base import ChangeSource
from infraops_core.models.change_event import ChangeEvent


class MerakiClient(ChangeSource):
    """Minimal Meraki API wrapper focused on configuration change events."""

    def __init__(self, *, api_key: str, base_url: str = "https://api.meraki.com/api/v1") -> None:
        self._client = httpx.Client(base_url=base_url)
        self._auth = APIKeyAuth(header="X-Cisco-Meraki-API-Key", value=api_key)

    def list_changes(
        self, **filters: Any
    ) -> Iterable[ChangeEvent]:  # pragma: no cover - roadmap placeholder
        raise NotImplementedError("Meraki change ingestion is not implemented yet")


__all__ = ["MerakiClient"]
