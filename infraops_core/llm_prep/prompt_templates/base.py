"""Prompt template definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PromptTemplate:
    system: str
    user: str

    def render(self, *, context: dict[str, str]) -> dict[str, str]:
        return {
            "system": self.system.format(**context),
            "user": self.user.format(**context),
        }


__all__ = ["PromptTemplate"]
