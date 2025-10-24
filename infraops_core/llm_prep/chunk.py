"""Character-based chunking utilities for LLM preparation."""

from __future__ import annotations

from typing import Iterator


def chunk_text(text: str, *, size: int, overlap: int = 0) -> Iterator[str]:
    """Yield chunks of ``text`` with the requested character size.

    Parameters
    ----------
    text:
        The source text to split.
    size:
        Maximum number of characters in each chunk. Must be positive.
    overlap:
        Number of overlapping characters to include between sequential chunks.
        Must be zero or positive and smaller than ``size``.
    """

    if size <= 0:
        raise ValueError("size must be a positive integer")
    if overlap < 0:
        raise ValueError("overlap must be zero or positive")
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    if not text:
        return

    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(text_length, start + size)
        yield text[start:end]
        if end == text_length:
            break
        start = end - overlap


__all__ = ["chunk_text"]
