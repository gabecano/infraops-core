"""Authentication helpers for API integrations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import httpx


@dataclass(slots=True)
class APIKeyAuth:
    """Attach a static API key header to outgoing HTTP requests."""

    header: str
    value: str

    def apply(self, request: httpx.Request) -> None:
        request.headers[self.header] = self.value


@dataclass(slots=True)
class OAuthToken:
    """Represents an OAuth access token."""

    access_token: str
    token_type: str = "Bearer"

    def as_header(self) -> str:
        return f"{self.token_type} {self.access_token}"


class AuthenticatedClient(httpx.Client):
    """HTTP client that injects authentication headers."""

    def __init__(self, *, auth_headers: Mapping[str, str], **kwargs: Any) -> None:
        headers = {**dict(kwargs.pop("headers", {})), **auth_headers}
        super().__init__(headers=headers, **kwargs)


__all__ = ["APIKeyAuth", "OAuthToken", "AuthenticatedClient"]
