"""Utilities to redact sensitive values prior to LLM ingestion."""

from __future__ import annotations

import re
from collections.abc import Iterable

REDACTION_TOKEN = "[REDACTED]"  # noqa: S105 - constant redaction marker

_IP_PATTERN = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
)
_EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_TOKEN_PATTERN = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9]{20,}(?![A-Za-z0-9])")


def redact(
    text: str,
    *,
    secrets: Iterable[str] | None = None,
    extra_patterns: Iterable[str] | None = None,
) -> str:
    """Redact secrets, IP addresses, API tokens, and email addresses.

    Parameters
    ----------
    text:
        Source text to clean.
    secrets:
        Optional explicit secrets to replace verbatim.
    extra_patterns:
        Additional regular expressions to evaluate in addition to the built-ins.
    """

    result = text
    for secret in secrets or []:
        if not secret:
            continue
        result = result.replace(secret, REDACTION_TOKEN)

    for builtin_pattern in (_IP_PATTERN, _EMAIL_PATTERN, _TOKEN_PATTERN):
        result = builtin_pattern.sub(REDACTION_TOKEN, result)

    for extra_pattern in extra_patterns or []:
        result = re.sub(extra_pattern, REDACTION_TOKEN, result, flags=re.IGNORECASE)

    return result


__all__ = ["REDACTION_TOKEN", "redact"]
