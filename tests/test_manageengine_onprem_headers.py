from __future__ import annotations

import pytest
import respx
from httpx import Response
from infraops_core.clients.manageengine import ManageEngineClient


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    from infraops_core.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]


@respx.mock
def test_onprem_uses_authtoken_header(respx_mock: respx.Router) -> None:
    base_url = "http://sdp.local:8080"
    route = respx_mock.get(f"{base_url}/api/v3/changes").mock(
        return_value=Response(200, json={"list_info": {"row_count": 0}, "changes": []})
    )

    manageengine = ManageEngineClient(base_url=base_url, api_key="secret", page_size=1)
    list(manageengine.list_changes())
    manageengine.close()

    assert route.called
    request = route.calls.last.request  # type: ignore[union-attr]
    assert request.headers["authtoken"] == "secret"
    assert request.headers["Accept"] == "application/vnd.manageengine.sdp.v3+json"
    assert "Authorization" not in request.headers


@respx.mock
def test_portal_base_url_is_supported(respx_mock: respx.Router) -> None:
    base_url = "https://example.com/app/portal"
    route = respx_mock.get(f"{base_url}/api/v3/changes").mock(
        return_value=Response(200, json={"list_info": {"row_count": 0}, "changes": []})
    )

    manageengine = ManageEngineClient(base_url=base_url, api_key="secret", page_size=1)
    list(manageengine.list_changes())
    manageengine.close()

    assert route.called


@respx.mock
def test_existing_api_base_is_respected(respx_mock: respx.Router) -> None:
    base_url = "https://example.com/api/v3"
    route = respx_mock.get(f"{base_url}/changes").mock(
        return_value=Response(200, json={"list_info": {"row_count": 0}, "changes": []})
    )

    manageengine = ManageEngineClient(base_url=base_url, api_key="secret", page_size=1)
    list(manageengine.list_changes())
    manageengine.close()

    assert route.called
