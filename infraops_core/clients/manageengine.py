"""ManageEngine ServiceDesk Plus API client."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from datetime import datetime
from typing import Any, cast, overload

import httpx

from infraops_core.clients.base import ChangeSource
from infraops_core.config import get_settings
from infraops_core.http.client import create_sync_client, retryable
from infraops_core.logging import get_logger
from infraops_core.models.change_event import Approval, ChangeEvent, ConfigDiff

_LOGGER = get_logger(__name__)


class AuthError(RuntimeError):
    """Raised when ManageEngine responds with an authentication prompt."""


_ACCEPT_HEADER = "application/vnd.manageengine.sdp.v3+json"


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


def _unwrap_field(value: Any) -> Any:
    """Return the innermost scalar value from nested ManageEngine fields."""

    seen: set[int] = set()
    current = value
    while isinstance(current, Mapping):
        marker = id(current)
        if marker in seen:
            break
        seen.add(marker)
        if "value" in current and current["value"] not in (None, "", {}):
            current = current["value"]
            continue
        if "display_value" in current and current["display_value"] not in (None, ""):
            return current["display_value"]
        break
    return current


def _looks_like_login_page(text: str) -> bool:
    lowered = text.lower()
    return "<html" in lowered and ("login" in lowered or "signin" in lowered)


def _coerce_int(value: Any) -> int | None:
    """Best-effort conversion of ManageEngine numeric fields to integers."""

    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _build_api_base(url: str) -> str:
    parsed = httpx.URL(url)
    path = parsed.path.rstrip("/")
    if path.endswith("/api/v3"):
        return str(parsed.copy_with(path=path or "/"))
    if path:
        path = f"{path}/api/v3"
    else:
        path = "/api/v3"
    return str(parsed.copy_with(path=path))


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
        self._api_base_url = _build_api_base(self._base_url)
        headers = {"authtoken": self._api_key, "Accept": _ACCEPT_HEADER}
        self._client = client or create_sync_client(base_url=self._api_base_url, headers=headers)

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
            start_index = 1
            requested = effective_page_size
            while True:
                params = self._build_query(query_filters, offset=start_index, page_size=requested)
                payload = self._fetch_page(params)
                changes = list(self._transform_payload(payload))
                yield from changes
                list_info = cast(dict[str, Any], payload.get("list_info", {}) or {})
                returned = _coerce_int(list_info.get("row_count"))
                if returned is None:
                    returned = len(changes)
                has_more: bool | None
                has_more_raw = list_info.get("has_more_rows")
                if isinstance(has_more_raw, str):
                    has_more = has_more_raw.lower() == "true"
                elif isinstance(has_more_raw, bool):
                    has_more = has_more_raw
                else:
                    has_more = None
                if not changes or returned < requested or has_more is False:
                    break
                start = _coerce_int(list_info.get("start_index"))
                if start is None:
                    start = start_index
                start_index = start + max(returned, len(changes))

        return generator()

    def _build_query(
        self, filters: Mapping[str, object], *, offset: int, page_size: int
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "list_info": json.dumps({"row_count": page_size, "start_index": offset}),
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
        response = self._client.get("changes", params=params)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if "html" in content_type:
            raise AuthError("Check authtoken or base URL")
        try:
            data = response.json()
        except ValueError as exc:
            if _looks_like_login_page(response.text):
                raise AuthError("Check authtoken or base URL") from exc
            raise
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
        approvals = []
        for item in raw.get("approvals", []) or []:
            approver = _unwrap_field(item.get("approver", {}).get("name", "unknown"))
            status = _unwrap_field(item.get("status", "unknown"))
            responded = _unwrap_field(item.get("responded_time") or item.get("approval_time"))
            approvals.append(
                Approval(
                    approver=str(approver or "unknown"),
                    status=str(status or "unknown"),
                    responded_at=_parse_datetime(responded),
                )
            )
        diffs = [
            ConfigDiff(
                path=diff.get("field", ""),
                before=str(diff.get("old_value")) if diff.get("old_value") is not None else None,
                after=str(diff.get("new_value")) if diff.get("new_value") is not None else None,
            )
            for diff in raw.get("changes", []) or []
        ]
        implemented_at = _parse_datetime(_unwrap_field(raw.get("implemented_time")))
        submitted_at = _parse_datetime(_unwrap_field(raw.get("created_time")))
        if submitted_at is None:
            raise ValueError("Change missing creation time")

        raw_payload = cast(dict[str, Any], raw)

        service_name = _unwrap_field(raw.get("service", {}).get("name", "unknown"))
        requester_name = _unwrap_field(raw.get("requester", {}).get("name", "unknown"))
        risk_value = _unwrap_field(raw.get("risk", {}).get("name"))
        if risk_value is None and raw.get("risk_level") is not None:
            risk_value = raw.get("risk_level")

        summary = _unwrap_field(raw.get("title"))
        if summary in (None, ""):
            summary = raw.get("subject", "")

        description = _unwrap_field(raw.get("description", ""))

        return ChangeEvent(
            id=str(raw.get("id")),
            submitted_at=submitted_at,
            implemented_at=implemented_at,
            service=str(service_name or "unknown"),
            requester=str(requester_name or "unknown"),
            risk=str(risk_value) if risk_value not in (None, "") else None,
            summary=str(summary or ""),
            description=str(description or ""),
            approvals=approvals,
            diffs=diffs,
            raw=raw_payload,
        )

    def _post(self, path: str, payload: Mapping[str, Any]) -> httpx.Response:
        data = {"input_data": json.dumps(payload)}
        return self._client.post(
            path,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )


__all__ = ["AuthError", "ManageEngineClient"]
