"""Device model shared across integrations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Device:
    id: str
    name: str
    ip_address: str | None = None
    site: str | None = None
    vendor: str | None = None


__all__ = ["Device"]
