"""Tests for JSONL writer helpers."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

from infraops_core.io.jsonl import write_jsonl


def test_write_jsonl_writes_newline_terminated_records() -> None:
    buffer = StringIO()
    rows = [{"id": 1}, {"id": 2}]
    write_jsonl(rows, buffer)

    contents = buffer.getvalue()
    assert contents.endswith("\n")
    assert contents.count("\n") == len(rows)
    loaded = [json.loads(line) for line in contents.splitlines()]
    assert loaded == rows


def test_write_jsonl_handles_unicode(tmp_path: Path) -> None:
    destination = tmp_path / "data" / "changes.jsonl"
    write_jsonl([{"message": "こんにちは世界"}], destination)

    data = destination.read_text(encoding="utf-8").splitlines()
    assert data and json.loads(data[0]) == {"message": "こんにちは世界"}
