"""ManageEngine ServiceDesk Plus API client."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any, Iterator, Mapping, cast, overload

import httpx

from infraops_core.clients.base import ChangeSource
from infraops_core.config import get_settings
from infraops_core.http.client import create_sync_client, retryable
from infraops_core.logging import get_logger
from infraops_core.models.change_event import Approval, ChangeEvent, ConfigDiff

_LOGGER = get_logger(__name__)


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, "", 0):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value))
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    raise ValueError(f"Unsupported datetime value: {value!r}")


class ManageEngineClient(ChangeSource):
    """Thin wrapper around the ManageEngine ServiceDesk Plus v3 API."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        page_size: int = 200,
    ) -> None:
        settings = get_settings()
        self._base_url = base_url or (
            str(settings.manageengine_base_url) if settings.manageengine_base_url else None
        )
        if not self._base_url:
            raise ValueError("ManageEngine base URL must be configured")
        self._api_key = api_key or settings.manageengine_api_key
        if not self._api_key:
            raise ValueError("ManageEngine API key must be provided")
        self._page_size = page_size
        headers = {"TECHNICIAN_KEY": self._api_key, "Accept": "application/json"}
        self._client = client or create_sync_client(base_url=self._base_url, headers=headers)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ManageEngineClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    @overload
    def list_changes(
        self,
        *,
        start: datetime | None = ...,
        end: datetime | None = ...,
        status: str | None = ...,
        requester: str | None = ...,
        service: str | None = ...,
        page_size: int | None = ...,
    ) -> Iterable[ChangeEvent]: ...

    @overload
    def list_changes(self, **filters: object) -> Iterable[ChangeEvent]: ...

    def list_changes(self, **filters: object) -> Iterable[ChangeEvent]:
        start = cast(datetime | None, filters.pop("start", None))
        end = cast(datetime | None, filters.pop("end", None))
        status = cast(str | None, filters.pop("status", None))
        requester = cast(str | None, filters.pop("requester", None))
        service = cast(str | None, filters.pop("service", None))
        page_size = cast(int | None, filters.pop("page_size", None))

        if filters:
            unsupported = ", ".join(sorted(filters))
            raise TypeError(f"Unsupported filters provided: {unsupported}")

        effective_page_size = page_size or self._page_size

        query_filters: dict[str, object] = {}
        if start is not None:
            query_filters["start_time"] = start
        if end is not None:
            query_filters["end_time"] = end
        if status is not None:
            query_filters["status"] = status
        if requester is not None:
            query_filters["requester"] = requester
        if service is not None:
            query_filters["service"] = service

        def generator() -> Iterator[ChangeEvent]:
            total_records: int | None = None
            offset = 0
            while True:
                params = self._build_query(
                    query_filters, offset=offset, page_size=effective_page_size
                )
                payload = self._fetch_page(params)
                total_records = cast(int | None, payload.get("total_count", total_records))
                yield from self._transform_payload(payload)
                offset += effective_page_size
                if total_records is None or offset >= total_records:
                    break

        return generator()

    def _build_query(
        self, filters: Mapping[str, object], *, offset: int, page_size: int
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "limit": page_size,
            "start_index": offset,
        }
        start_time = filters.get("start_time")
        end_time = filters.get("end_time")
        if start_time is not None:
            parsed = _parse_datetime(start_time)
            if parsed is not None:
                params["created_time_after"] = int(parsed.timestamp())
        if end_time is not None:
            parsed = _parse_datetime(end_time)
            if parsed is not None:
                params["created_time_before"] = int(parsed.timestamp())
        if "status" in filters:
            params["status"] = filters["status"]
        if "requester" in filters:
            params["requester.name"] = filters["requester"]
        if "service" in filters:
            params["service.name"] = filters["service"]
        return params

    @retryable
    def _fetch_page(self, params: dict[str, Any]) -> dict[str, Any]:
        response = self._client.get("/api/v3/changes", params=params)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):  # pragma: no cover - defensive guard
            raise ValueError("Unexpected ManageEngine response payload")
        return cast(dict[str, Any], data)

    def _transform_payload(self, payload: dict[str, Any]) -> Iterator[ChangeEvent]:
        for raw in payload.get("changes", []) or []:
            if not isinstance(raw, dict):  # pragma: no cover - defensive guard
                _LOGGER.warning("Skipping non-dict ManageEngine change payload", raw=raw)
                continue
            try:
                yield self._to_change_event(raw)
            except Exception as exc:  # pragma: no cover - defensive logging
                _LOGGER.error("Failed to parse ManageEngine change", error=str(exc), raw=raw)

    def _to_change_event(self, raw: dict[str, Any]) -> ChangeEvent:
        approvals = [
            Approval(
                approver=item.get("approver", {}).get("name", "unknown"),
                status=item.get("status", "unknown"),
                responded_at=_parse_datetime(item.get("approval_time")),
            )
            for item in raw.get("approvals", []) or []
        ]
        diffs = [
            ConfigDiff(
                path=diff.get("field", ""),
                before=str(diff.get("old_value")) if diff.get("old_value") is not None else None,
                after=str(diff.get("new_value")) if diff.get("new_value") is not None else None,
            )
            for diff in raw.get("changes", []) or []
        ]
        implemented_at = _parse_datetime(raw.get("implemented_time"))
        submitted_at = _parse_datetime(raw.get("created_time"))
        if submitted_at is None:
            raise ValueError("Change missing creation time")

        raw_payload = cast(dict[str, Any], raw)

        return ChangeEvent(
            id=str(raw.get("id")),
            submitted_at=submitted_at,
            implemented_at=implemented_at,
            service=raw.get("service", {}).get("name", "unknown"),
            requester=raw.get("requester", {}).get("name", "unknown"),
            risk=raw.get("risk_level"),
            summary=raw.get("subject", ""),
            description=raw.get("description", ""),
            approvals=approvals,
            diffs=diffs,
            raw=raw_payload,
        )


__all__ = ["ManageEngineClient"]
