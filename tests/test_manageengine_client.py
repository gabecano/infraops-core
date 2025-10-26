from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import parse_qs

import pytest
from httpx import Client, MockTransport, Request, Response
from infraops_core.clients.manageengine import (
    _ACCEPT_HEADER,
    AuthError,
    ManageEngineClient,
    _build_api_base,
    _parse_datetime,
)


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    from infraops_core.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]


def _build_mock_client(base_url: str, handler: MockTransport | None = None) -> Client:
    api_base = _build_api_base(base_url)
    transport = handler or MockTransport(lambda request: Response(500))
    return Client(
        base_url=api_base,
        transport=transport,
        headers={"authtoken": "token", "Accept": _ACCEPT_HEADER},
    )


def test_list_changes_maps_fields() -> None:
    base_url = "https://example.com"
    payload = {
        "list_info": {"row_count": 1, "has_more_rows": False, "start_index": 1},
        "changes": [
            {
                "id": "1001",
                "title": {"display_value": "Network change"},
                "description": {"display_value": "Added VLAN"},
                "created_time": "2024-04-02T12:00:00",
                "implemented_time": {"display_value": "2024-04-02T13:00:00"},
                "service": {"name": {"display_value": "Network"}},
                "requester": {"name": "alice"},
                "risk": {"name": "Low"},
                "approvals": [
                    {
                        "approver": {"name": {"display_value": "bob"}},
                        "status": {"display_value": "approved"},
                        "responded_time": "2024-04-02T12:30:00",
                    }
                ],
                "changes": [],
            }
        ],
    }

    def handler(request: Request) -> Response:
        assert request.url.path.endswith("/changes")
        return Response(200, json=payload)

    client = _build_mock_client(base_url, MockTransport(handler))
    manageengine = ManageEngineClient(base_url=base_url, api_key="token", client=client)

    events = list(manageengine.list_changes())
    manageengine.close()

    assert len(events) == 1
    event = events[0]
    assert event.id == "1001"
    assert event.summary == "Network change"
    assert event.description == "Added VLAN"
    assert event.service == "Network"
    assert event.risk == "Low"
    assert event.requester == "alice"
    assert event.approvals[0].approver == "bob"
    assert event.approvals[0].status == "approved"
    assert event.approvals[0].responded_at is not None
    assert event.raw["title"]["display_value"] == "Network change"


def test_list_changes_skips_null_approvals(capsys: pytest.CaptureFixture[str]) -> None:
    base_url = "https://example.com"
    payload = {
        "list_info": {"row_count": 1, "has_more_rows": False, "start_index": 1},
        "changes": [
            {
                "id": "2002",
                "title": {"display_value": "Firewall change"},
                "description": {"display_value": "Adjusted rules"},
                "created_time": "2024-04-02T12:00:00",
                "approvals": [None, {"approver": {"name": {"display_value": "lee"}}}],
            }
        ],
    }

    def handler(_: Request) -> Response:
        return Response(200, json=payload)

    client = _build_mock_client(base_url, MockTransport(handler))
    manageengine = ManageEngineClient(base_url=base_url, api_key="token", client=client)

    events = list(manageengine.list_changes())
    manageengine.close()

    assert len(events) == 1
    event = events[0]
    assert len(event.approvals) == 1
    assert event.approvals[0].approver == "lee"
    assert event.approvals[0].status == "unknown"
    captured = capsys.readouterr()
    assert "Skipping non-mapping ManageEngine approval entry" in captured.out


def test_list_changes_handles_missing_approver_mapping() -> None:
    base_url = "https://example.com"
    payload = {
        "list_info": {"row_count": 1, "has_more_rows": False, "start_index": 1},
        "changes": [
            {
                "id": "3003",
                "title": {"display_value": "Switch change"},
                "description": {"display_value": "Updated firmware"},
                "created_time": "2024-04-02T12:00:00",
                "approvals": [
                    {
                        "approver": None,
                        "status": {"display_value": "Approved"},
                        "approval_time": {"display_value": "2024-04-02T12:15:00"},
                    }
                ],
            }
        ],
    }

    def handler(_: Request) -> Response:
        return Response(200, json=payload)

    client = _build_mock_client(base_url, MockTransport(handler))
    manageengine = ManageEngineClient(base_url=base_url, api_key="token", client=client)

    events = list(manageengine.list_changes())
    manageengine.close()

    assert len(events) == 1
    event = events[0]
    assert len(event.approvals) == 1
    approval = event.approvals[0]
    assert approval.approver == "unknown"
    assert approval.status == "Approved"
    assert approval.responded_at is not None


def test_list_changes_logs_missing_nested_mappings(
    capsys: pytest.CaptureFixture[str],
) -> None:
    base_url = "https://example.com"
    payload = {
        "list_info": {"row_count": 1, "has_more_rows": False, "start_index": 1},
        "changes": [
            {
                "id": "4004",
                "title": {"display_value": "Router update"},
                "description": {"display_value": "Applied patches"},
                "created_time": "2024-04-02T12:00:00",
                "service": None,
                "requester": None,
                "risk": "unexpected",
                "risk_level": "Moderate",
            }
        ],
    }

    def handler(_: Request) -> Response:
        return Response(200, json=payload)

    client = _build_mock_client(base_url, MockTransport(handler))
    manageengine = ManageEngineClient(base_url=base_url, api_key="token", client=client)

    events = list(manageengine.list_changes())
    manageengine.close()

    assert len(events) == 1
    event = events[0]
    assert event.service == "unknown"
    assert event.requester == "unknown"
    assert event.risk == "Moderate"

    captured = capsys.readouterr()
    assert "ManageEngine change missing mapping field" in captured.out
    assert "field=service" in captured.out
    assert "ManageEngine change field is not a mapping" in captured.out


def test_list_changes_applies_filters() -> None:
    base_url = "https://example.com"
    captured: list[Request] = []

    def handler(request: Request) -> Response:
        captured.append(request)
        return Response(
            200,
            json={
                "list_info": {"row_count": 0, "has_more_rows": False, "start_index": 1},
                "changes": [],
            },
        )

    client = _build_mock_client(base_url, MockTransport(handler))
    manageengine = ManageEngineClient(
        base_url=base_url, api_key="token", page_size=100, client=client
    )

    list(
        manageengine.list_changes(
            start=datetime(2024, 5, 1, 10, 0, 0),
            end=datetime(2024, 5, 2, 10, 0, 0),
            status="closed",
            requester="dan",
            service="Network",
        )
    )
    manageengine.close()

    assert captured
    request = captured[-1]
    params = request.url.params
    assert params["requester.name"] == "dan"
    assert params["service.name"] == "Network"
    assert int(params["created_time_after"]) < int(params["created_time_before"])
    payload = json.loads(params["input_data"])
    list_info = payload["list_info"]
    assert list_info["row_count"] == 100
    assert list_info["start_index"] == 0
    assert list_info.get("filter_by", {}).get("status") == "closed"


def test_fetch_page_raises_auth_error_on_html() -> None:
    base_url = "https://example.com"

    def handler(_: Request) -> Response:
        return Response(
            200,
            text="<html><body>Login required</body></html>",
            headers={"Content-Type": "text/html"},
        )

    client = _build_mock_client(base_url, MockTransport(handler))
    manageengine = ManageEngineClient(base_url=base_url, api_key="token", client=client)

    with pytest.raises(AuthError):
        list(manageengine.list_changes())

    manageengine.close()


def test_fetch_page_raises_auth_error_on_login_body() -> None:
    base_url = "https://example.com"

    def handler(_: Request) -> Response:
        return Response(
            200,
            text="<html><title>Login</title></html>",
            headers={"Content-Type": "application/json"},
        )

    client = _build_mock_client(base_url, MockTransport(handler))
    manageengine = ManageEngineClient(base_url=base_url, api_key="token", client=client)

    with pytest.raises(AuthError):
        list(manageengine.list_changes())

    manageengine.close()


def test_fetch_page_raises_auth_error_on_non_json() -> None:
    base_url = "https://example.com"

    def handler(_: Request) -> Response:
        return Response(
            200,
            text="Invalid token",
            headers={"Content-Type": "text/plain"},
        )

    client = _build_mock_client(base_url, MockTransport(handler))
    manageengine = ManageEngineClient(base_url=base_url, api_key="token", client=client)

    with pytest.raises(AuthError):
        list(manageengine.list_changes())

    manageengine.close()


def test_post_wraps_payload() -> None:
    base_url = "https://example.com"
    captured: list[Request] = []

    def handler(request: Request) -> Response:
        captured.append(request)
        return Response(201, json={"status": "ok"})

    client = _build_mock_client(base_url, MockTransport(handler))
    manageengine = ManageEngineClient(base_url=base_url, api_key="token", client=client)

    response = manageengine._post("custom", {"foo": "bar"})
    manageengine.close()

    assert response.status_code == 201
    request = captured[-1]
    assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert request.headers["Accept"] == _ACCEPT_HEADER
    decoded = parse_qs(request.content.decode())
    assert "input_data" in decoded
    payload = json.loads(decoded["input_data"][0])
    assert payload == {"foo": "bar"}


def test_parse_datetime_supports_millisecond_epochs() -> None:
    expected = datetime.fromtimestamp(1512974940)
    assert _parse_datetime("1512974940000") == expected
    assert _parse_datetime(1512974940000) == expected
