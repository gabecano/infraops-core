"""Utilities to redact secrets and PII prior to LLM ingestion."""

from __future__ import annotations

import re
from typing import Iterable

REDACTION_TOKEN = "[REDACTED]"  # noqa: S105 - constant redaction marker


def redact(
    text: str, secrets: Iterable[str] | None = None, pii_patterns: Iterable[str] | None = None
) -> str:
    """Redact secrets and simple PII patterns from text."""

    result = text
    for secret in secrets or []:
        if not secret:
            continue
        result = result.replace(secret, REDACTION_TOKEN)
    for pattern in pii_patterns or []:
        result = re.sub(pattern, REDACTION_TOKEN, result, flags=re.IGNORECASE)
    return result


__all__ = ["redact", "REDACTION_TOKEN"]
