from __future__ import annotations

from datetime import datetime

import pytest
import respx
from httpx import Response
from infraops_core.clients.manageengine import ManageEngineClient


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    from infraops_core.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]


@respx.mock
def test_pagination_advances_start_index(respx_mock: respx.Router) -> None:
    base_url = "https://example.com"

    def handler(request):
        params = request.url.params
        start_index = params["list_info[start_index]"]
        if start_index == "0":
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
        assert start_index == "2"
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

    route = respx_mock.get(f"{base_url}/api/v3/changes").mock(side_effect=handler)

    manageengine = ManageEngineClient(base_url=base_url, api_key="secret", page_size=2)
    events = list(manageengine.list_changes())
    manageengine.close()

    assert route.call_count == 2
    assert [event.id for event in events] == ["1001", "1002", "1003"]
