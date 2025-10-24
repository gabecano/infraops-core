"""JSON Lines IO helpers."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import TextIO


def write_jsonl(rows: Iterable[dict[str, object]], path: str | Path | TextIO) -> None:
    """Write an iterable of dictionaries to JSON Lines."""

    if isinstance(path, (str, Path)):
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8") as stream:
            write_jsonl(rows, stream)
        return

    handle: TextIO = path
    for row in rows:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    handle.flush()


__all__ = ["write_jsonl"]
