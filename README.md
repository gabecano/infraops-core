# infraops-core

Reusable infrastructure operations library housing shared authentication helpers, HTTP utilities,
API clients, canonical models, ETL primitives, and LLM preparation helpers used across the
`meraki-backup` and `auditing` applications.

## Features

* Typed configuration with environment and `.env` support
* HTTP clients with retry/backoff helpers powered by Tenacity and httpx
* ManageEngine client producing canonical `ChangeEvent` models
* Stubs for Meraki, SolarWinds, Veeam, and DNS change sources for future build out
* ETL pipeline primitives and IO helpers (JSONL writer)
* LLM preparation utilities covering redaction, chunking, and prompt templates

## Getting started

```bash
poetry install
poetry run pytest
```

## Releasing

1. Update the version in `pyproject.toml`
2. Run tests and quality checks: `poetry run ruff check && poetry run pytest`
3. Create a SemVer tag and push to trigger the publish workflow
