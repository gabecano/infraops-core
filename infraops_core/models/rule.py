"""Common policy rule model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Rule:
    id: str
    name: str
    description: str | None = None
    severity: str | None = None


__all__ = ["Rule"]
