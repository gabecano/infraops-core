from __future__ import annotations

import pytest
from httpx import Client, MockTransport, Request, Response
from infraops_core.clients.manageengine import _ACCEPT_HEADER, ManageEngineClient, _build_api_base


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    from infraops_core.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]


def _client_with_handler(base_url: str, handler: MockTransport) -> Client:
    return Client(
        base_url=_build_api_base(base_url),
        transport=handler,
        headers={"authtoken": "secret", "Accept": _ACCEPT_HEADER},
    )


def test_onprem_uses_authtoken_header() -> None:
    base_url = "http://sdp.local:8080"
    captured: list[Request] = []

    def handler(request: Request) -> Response:
        captured.append(request)
        return Response(200, json={"list_info": {"row_count": 0}, "changes": []})

    manageengine = ManageEngineClient(
        base_url=base_url,
        api_key="secret",
        page_size=1,
        client=_client_with_handler(base_url, MockTransport(handler)),
    )
    list(manageengine.list_changes())
    manageengine.close()

    request = captured[-1]
    assert request.headers["authtoken"] == "secret"
    assert request.headers["Accept"] == "application/vnd.manageengine.sdp.v3+json"
    assert "Authorization" not in request.headers


def test_portal_base_url_is_supported() -> None:
    base_url = "https://example.com/app/portal"

    def handler(_: Request) -> Response:
        return Response(200, json={"list_info": {"row_count": 0}, "changes": []})

    manageengine = ManageEngineClient(
        base_url=base_url,
        api_key="secret",
        page_size=1,
        client=_client_with_handler(base_url, MockTransport(handler)),
    )
    list(manageengine.list_changes())
    manageengine.close()


def test_existing_api_base_is_respected() -> None:
    base_url = "https://example.com/api/v3"

    def handler(_: Request) -> Response:
        return Response(200, json={"list_info": {"row_count": 0}, "changes": []})

    manageengine = ManageEngineClient(
        base_url=base_url,
        api_key="secret",
        page_size=1,
        client=_client_with_handler(base_url, MockTransport(handler)),
    )
    list(manageengine.list_changes())
    manageengine.close()
