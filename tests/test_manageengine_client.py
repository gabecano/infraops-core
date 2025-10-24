from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import parse_qs

import pytest
import respx
from httpx import Response
from infraops_core.clients.manageengine import AuthError, ManageEngineClient


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    from infraops_core.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]


@respx.mock
def test_list_changes_maps_fields(respx_mock: respx.Router) -> None:
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

    respx_mock.get(f"{base_url}/api/v3/changes").mock(return_value=Response(200, json=payload))

    manageengine = ManageEngineClient(base_url=base_url, api_key="token")

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


@respx.mock
def test_list_changes_applies_filters(respx_mock: respx.Router) -> None:
    base_url = "https://example.com"
    route = respx_mock.get(f"{base_url}/api/v3/changes").mock(
        return_value=Response(
            200,
            json={
                "list_info": {"row_count": 0, "has_more_rows": False, "start_index": 1},
                "changes": [],
            },
        )
    )

    manageengine = ManageEngineClient(
        base_url=base_url,
        api_key="token",
        page_size=100,
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

    assert route.called
    request = route.calls.last.request  # type: ignore[union-attr]
    params = request.url.params
    assert params["status"] == "closed"
    assert params["requester.name"] == "dan"
    assert params["service.name"] == "Network"
    assert int(params["created_time_after"]) < int(params["created_time_before"])
    assert params["list_info[row_count]"] == "100"
    assert params["list_info[start_index]"] == "0"


@respx.mock
def test_fetch_page_raises_auth_error_on_html(respx_mock: respx.Router) -> None:
    base_url = "https://example.com"
    respx_mock.get(f"{base_url}/api/v3/changes").mock(
        return_value=Response(
            200,
            text="<html><body>Login required</body></html>",
            headers={"Content-Type": "text/html"},
        )
    )

    manageengine = ManageEngineClient(base_url=base_url, api_key="token")

    with pytest.raises(AuthError):
        list(manageengine.list_changes())

    manageengine.close()


@respx.mock
def test_fetch_page_raises_auth_error_on_login_body(respx_mock: respx.Router) -> None:
    base_url = "https://example.com"
    respx_mock.get(f"{base_url}/api/v3/changes").mock(
        return_value=Response(
            200,
            text="<html><title>Login</title></html>",
            headers={"Content-Type": "application/json"},
        )
    )

    manageengine = ManageEngineClient(base_url=base_url, api_key="token")

    with pytest.raises(AuthError):
        list(manageengine.list_changes())

    manageengine.close()


@respx.mock
def test_fetch_page_raises_auth_error_on_non_json(respx_mock: respx.Router) -> None:
    base_url = "https://example.com"
    respx_mock.get(f"{base_url}/api/v3/changes").mock(
        return_value=Response(
            200,
            text="Invalid token",
            headers={"Content-Type": "text/plain"},
        )
    )

    manageengine = ManageEngineClient(base_url=base_url, api_key="token")

    with pytest.raises(AuthError):
        list(manageengine.list_changes())

    manageengine.close()


@respx.mock
def test_post_wraps_payload(respx_mock: respx.Router) -> None:
    base_url = "https://example.com"
    route = respx_mock.post(f"{base_url}/api/v3/custom").mock(
        return_value=Response(201, json={"status": "ok"})
    )

    manageengine = ManageEngineClient(base_url=base_url, api_key="token")

    response = manageengine._post("custom", {"foo": "bar"})
    manageengine.close()

    assert response.status_code == 201
    request = route.calls.last.request  # type: ignore[union-attr]
    assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert request.headers["Accept"] == "application/vnd.manageengine.sdp.v3+json"
    decoded = parse_qs(request.content.decode())
    assert "input_data" in decoded
    payload = json.loads(decoded["input_data"][0])
    assert payload == {"foo": "bar"}
