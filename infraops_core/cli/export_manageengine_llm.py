"""Export ManageEngine changes to JSONL with LLM-safe redaction."""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

from infraops_core.clients.manageengine import ManageEngineClient
from infraops_core.io.jsonl import write_jsonl
from infraops_core.llm_prep.redact import redact
from infraops_core.models.change_event import ChangeEvent

app = typer.Typer(help=__doc__ or "")


def _parse_iso8601(value: str | None, *, argument: str) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover - Typer will show the message
        raise typer.BadParameter(f"Invalid ISO-8601 timestamp for {argument}: {value}") from exc


def _iter_redacted_rows(events: Iterable[ChangeEvent]) -> Iterator[dict[str, object]]:
    for event in events:
        record = event.model_dump()
        record["summary"] = redact(record.get("summary", ""))
        record["description"] = redact(record.get("description", ""))
        record["service"] = redact(record.get("service", ""))
        record["requester"] = redact(record.get("requester", ""))
        record["approvals"] = [
            {
                **approval,
                "approver": redact(str(approval.get("approver", ""))),
            }
            for approval in record.get("approvals", [])
        ]
        yield record


ALLOWED_STATUSES = {"implemented", "approved"}


def _validate_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalised = value.lower()
    if normalised not in ALLOWED_STATUSES:
        allowed = ", ".join(sorted(ALLOWED_STATUSES))
        raise typer.BadParameter(f"Status must be one of: {allowed}")
    return normalised


StatusOption = Annotated[
    str | None,
    typer.Option(
        help="Restrict to changes with the given status.",
        callback=_validate_status,
    ),
]
FromOption = Annotated[str | None, typer.Option("--from", help="ISO-8601 start timestamp.")]
ToOption = Annotated[str | None, typer.Option("--to", help="ISO-8601 end timestamp.")]
OutOption = Annotated[
    Path | None,
    typer.Option("--out", help="Path to write JSONL output.", dir_okay=False, writable=True),
]
PageSizeOption = Annotated[
    int,
    typer.Option(
        "--page-size",
        min=1,
        help="Number of records to request per page from ManageEngine.",
        show_default=True,
        default=100,
    ),
]


@app.command("export")
def export_manageengine_llm(
    *,
    status: StatusOption = None,
    from_: FromOption = None,
    to: ToOption = None,
    out: OutOption = None,
    page_size: PageSizeOption = 100,
) -> None:
    """Stream ManageEngine change events to a JSONL file ready for LLM ingestion."""

    base_url = os.getenv("ME_BASE_URL")
    api_key = os.getenv("ME_API_KEY")
    missing = [
        name for name, value in (("ME_BASE_URL", base_url), ("ME_API_KEY", api_key)) if not value
    ]
    if missing:
        raise typer.BadParameter(
            "Environment variables ME_BASE_URL and ME_API_KEY must be set; missing "
            + ", ".join(missing)
        )

    start = _parse_iso8601(from_, argument="--from")
    end = _parse_iso8601(to, argument="--to")

    if out is None:
        raise typer.BadParameter("--out must be provided")

    with ManageEngineClient(base_url=base_url, api_key=api_key, page_size=page_size) as client:
        events = client.list_changes(status=status, start=start, end=end)
        write_jsonl(_iter_redacted_rows(events), out)


__all__ = ["app", "export_manageengine_llm"]
