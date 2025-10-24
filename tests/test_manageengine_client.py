from __future__ import annotations

from datetime import datetime

import httpx
import pytest
from infraops_core.clients.manageengine import ManageEngineClient


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    from infraops_core.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]


def test_list_changes_paginates() -> None:
    pages = {
        0: {
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
        1: {
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

    def handler(request: httpx.Request) -> httpx.Response:
        start_index = int(request.url.params.get("start_index", "0"))
        page = pages[start_index // 1]
        return httpx.Response(200, json=page)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(
        base_url="https://example.com", transport=transport, headers={"TECHNICIAN_KEY": "token"}
    )

    manageengine = ManageEngineClient(
        base_url="https://example.com",
        api_key="token",
        client=client,
        page_size=1,
    )

    events = list(manageengine.list_changes(status="approved"))
    manageengine.close()

    assert len(events) == 2
    assert events[0].id == "1001"
    assert events[0].approvals[0].approver == "bob"
    assert events[1].implemented_at is None


def test_list_changes_applies_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_params: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_params
        captured_params = dict(request.url.params)
        return httpx.Response(
            200,
            json={
                "total_count": 0,
                "changes": [],
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(
        base_url="https://example.com", transport=transport, headers={"TECHNICIAN_KEY": "token"}
    )

    manageengine = ManageEngineClient(
        base_url="https://example.com",
        api_key="token",
        client=client,
        page_size=1,
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

    assert captured_params["status"] == "closed"
    assert captured_params["requester.name"] == "dan"
    assert captured_params["service.name"] == "Network"
    assert int(captured_params["created_time_after"]) < int(captured_params["created_time_before"])
