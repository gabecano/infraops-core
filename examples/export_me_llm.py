"""Example library usage exporting ManageEngine changes for LLM ingestion."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

from infraops_core.clients.manageengine import ManageEngineClient
from infraops_core.io.jsonl import write_jsonl
from infraops_core.llm_prep.redact import redact
from infraops_core.models.change_event import ChangeEvent


def _redact_event(event: ChangeEvent) -> dict[str, object]:
    payload = event.model_dump()
    payload["summary"] = redact(payload.get("summary", ""))
    payload["description"] = redact(payload.get("description", ""))
    return payload


def main() -> None:
    base_url = os.environ["ME_BASE_URL"]
    api_key = os.environ["ME_API_KEY"]
    output = Path("./change_export.jsonl")
    start = datetime.utcnow() - timedelta(days=7)

    with ManageEngineClient(base_url=base_url, api_key=api_key) as client:
        events: Iterable[ChangeEvent] = client.list_changes(status="approved", start=start)
        write_jsonl((_redact_event(event) for event in events), output)

    print(f"Exported changes to {output}")


if __name__ == "__main__":
    main()
