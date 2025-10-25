from __future__ import annotations

import json
from datetime import datetime

import pytest
from httpx import Client, MockTransport, Request, Response
from infraops_core.clients.manageengine import _ACCEPT_HEADER, ManageEngineClient, _build_api_base


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    from infraops_core.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]


def test_pagination_advances_start_index() -> None:
    base_url = "https://example.com"

    def handler(request: Request) -> Response:
        params = request.url.params
        payload = json.loads(params["input_data"])
        start_index = payload["list_info"]["start_index"]
        if start_index == 0:
            timestamp = datetime.now().replace(microsecond=0).isoformat()
            return Response(
                200,
                json={
                    "list_info": {"row_count": 2, "has_more_rows": True, "start_index": 1},
                    "changes": [
                        {
                            "id": "1001",
                            "title": "First",
                            "description": "",
                            "created_time": timestamp,
                            "service": {"name": "Net"},
                            "requester": {"name": "alice"},
                        },
                        {
                            "id": "1002",
                            "title": "Second",
                            "description": "",
                            "created_time": timestamp,
                            "service": {"name": "Net"},
                            "requester": {"name": "bob"},
                        },
                    ],
                },
            )
        assert start_index == 2
        timestamp = datetime.now().replace(microsecond=0).isoformat()
        return Response(
            200,
            json={
                "list_info": {"row_count": 1, "has_more_rows": False, "start_index": 3},
                "changes": [
                    {
                        "id": "1003",
                        "title": "Third",
                        "description": "",
                        "created_time": timestamp,
                        "service": {"name": "Net"},
                        "requester": {"name": "carol"},
                    }
                ],
            },
        )

    transport = MockTransport(handler)
    manageengine = ManageEngineClient(
        base_url=base_url,
        api_key="secret",
        page_size=2,
        client=Client(
            base_url=_build_api_base(base_url),
            transport=transport,
            headers={"authtoken": "secret", "Accept": _ACCEPT_HEADER},
        ),
    )
    events = list(manageengine.list_changes())
    manageengine.close()

    assert len(events) == 3
    assert [event.id for event in events] == ["1001", "1002", "1003"]
