"""Canonical change management models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Protocol


@dataclass(slots=True)
class Approval:
    approver: str
    status: str
    responded_at: datetime | None = None


@dataclass(slots=True)
class ConfigDiff:
    path: str
    before: str | None
    after: str | None


@dataclass(slots=True)
class ChangeEvent:
    id: str
    submitted_at: datetime
    implemented_at: datetime | None
    service: str
    requester: str
    risk: str | None
    summary: str
    description: str
    approvals: list[Approval] = field(default_factory=list)
    diffs: list[ConfigDiff] = field(default_factory=list)

    def iter_approvals(self) -> Iterable[Approval]:
        return iter(self.approvals)

    def iter_diffs(self) -> Iterable[ConfigDiff]:
        return iter(self.diffs)


class ChangeEventTransformer(Protocol):
    """Protocol for normalising provider payloads into :class:`ChangeEvent`."""

    def __call__(self, payload: dict[str, object]) -> ChangeEvent: ...


__all__ = ["Approval", "ConfigDiff", "ChangeEvent", "ChangeEventTransformer"]
