"""Canonical change management models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterator, Protocol

from pydantic import BaseModel, ConfigDict, Field


class Approval(BaseModel):
    """Approval metadata for a change event."""

    model_config = ConfigDict(frozen=True)

    approver: str
    status: str
    responded_at: datetime | None = None


class ConfigDiff(BaseModel):
    """Representation of a configuration delta."""

    model_config = ConfigDict(frozen=True)

    path: str
    before: str | None = None
    after: str | None = None


class ChangeEvent(BaseModel):
    """Canonical representation of a change in infrastructure."""

    model_config = ConfigDict(frozen=True)

    id: str
    submitted_at: datetime
    implemented_at: datetime | None = None
    service: str
    requester: str
    risk: str | None = None
    summary: str
    description: str
    approvals: list[Approval] = Field(default_factory=list)
    diffs: list[ConfigDiff] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)

    def iter_approvals(self) -> Iterator[Approval]:
        return iter(self.approvals)

    def iter_diffs(self) -> Iterator[ConfigDiff]:
        return iter(self.diffs)


class ChangeEventTransformer(Protocol):
    """Protocol for normalising provider payloads into :class:`ChangeEvent`."""

    def __call__(self, payload: dict[str, object]) -> ChangeEvent: ...


__all__ = ["Approval", "ConfigDiff", "ChangeEvent", "ChangeEventTransformer"]
