from __future__ import annotations

from datetime import datetime

import httpx
import pytest
import respx
from httpx import Response
from infraops_core.clients.manageengine import ManageEngineClient


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    from infraops_core.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]


@respx.mock
def test_list_changes_paginates(respx_mock: respx.Router) -> None:
    base_url = "https://example.com"
    responses = {
        "0": {
            "total_count": 2,
            "changes": [
                {
                    "id": "1001",
                    "created_time": "2024-04-02T12:00:00",
                    "implemented_time": "2024-04-02T13:00:00",
                    "service": {"name": "Network"},
                    "requester": {"name": "alice"},
                    "risk_level": "low",
                    "subject": "Network change",
                    "description": "Added VLAN",
                    "approvals": [
                        {
                            "approver": {"name": "bob"},
                            "status": "approved",
                            "approval_time": "2024-04-02T12:30:00",
                        }
                    ],
                    "changes": [
                        {
                            "field": "vlan",
                            "old_value": "10",
                            "new_value": "20",
                        }
                    ],
                }
            ],
        },
        "1": {
            "total_count": 2,
            "changes": [
                {
                    "id": "1002",
                    "created_time": "2024-04-03T10:00:00",
                    "implemented_time": None,
                    "service": {"name": "Compute"},
                    "requester": {"name": "carol"},
                    "risk_level": None,
                    "subject": "Server patch",
                    "description": "Patched OS",
                    "approvals": [],
                    "changes": [],
                }
            ],
        },
    }

    def handler(request: httpx.Request) -> Response:
        start_index = request.url.params.get("start_index", "0")
        payload = responses[start_index]
        return Response(200, json=payload)

    respx_mock.get(f"{base_url}/api/v3/changes").mock(side_effect=handler)

    manageengine = ManageEngineClient(
        base_url=base_url,
        api_key="token",
        page_size=1,
    )

    events = list(manageengine.list_changes(status="approved"))
    manageengine.close()

    assert len(events) == 2
    assert events[0].id == "1001"
    assert events[0].approvals[0].approver == "bob"
    assert events[1].implemented_at is None
    assert events[0].raw["subject"] == "Network change"


@respx.mock
def test_list_changes_applies_filters(respx_mock: respx.Router) -> None:
    base_url = "https://example.com"
    route = respx_mock.get(f"{base_url}/api/v3/changes").mock(
        return_value=Response(
            200,
            json={
                "total_count": 0,
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
    params = route.calls.last.request.url.params  # type: ignore[union-attr]
    assert params["status"] == "closed"
    assert params["requester.name"] == "dan"
    assert params["service.name"] == "Network"
    assert int(params["created_time_after"]) < int(params["created_time_before"])
