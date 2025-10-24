"""SolarWinds API client."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import httpx

from infraops_core.auth import APIKeyAuth
from infraops_core.clients.base import ChangeSource
from infraops_core.models.change_event import ChangeEvent


class SolarWindsClient(ChangeSource):
    """Placeholder SolarWinds client with consistent interface."""

    def __init__(self, *, api_key: str, base_url: str) -> None:
        self._client = httpx.Client(base_url=base_url)
        self._auth = APIKeyAuth(header="Authorization", value=api_key)

    def list_changes(
        self, **filters: Any
    ) -> Iterable[ChangeEvent]:  # pragma: no cover - HTTP integration
        request = self._client.build_request("GET", "/changes", params=filters)
        self._auth.apply(request)
        response = self._client.send(request)
        response.raise_for_status()
        return []


__all__ = ["SolarWindsClient"]
