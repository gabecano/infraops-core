# infraops-core

Shared infrastructure operations toolkit with reusable API clients, canonical models, I/O helpers,
and LLM preparation utilities for downstream services such as **auditing** and **meraki-backup**.

## Quickstart

```bash
poetry install
poetry run pre-commit install
poetry run pytest
```

## Installation

The package is published to the GitHub Packages index. Configure Poetry to use the repository and
install a tagged release:

```bash
poetry config repositories.infraops-core "https://maven.pkg.github.com/<org>/infraops-core"
poetry config http-basic.infraops-core "<github-username>" "<github-token>"
poetry add infraops-core@<tag>
```

Consumers such as the **auditing** application should pin to a released tag and reuse the shared
clients/models rather than duplicating logic. The **meraki-backup** service can depend on the same
package today for shared utilities.

## Environment variables

| Variable | Description |
| --- | --- |
| `ME_BASE_URL` | Base URL for the ManageEngine ServiceDesk Plus instance. |
| `ME_API_KEY` | API key used for authentication. |
| `INFRAOPS_DEFAULT_TIMEOUT` | Optional override for default HTTP timeout (seconds). |
| `INFRAOPS_MAX_RETRY_ATTEMPTS` | Optional override for HTTP retry attempts. |

Copy `.env.example` and fill in the required ManageEngine settings:

```bash
cp .env.example .env
```

## On-Prem vs Cloud

| Aspect | On-Prem | Cloud |
| --- | --- | --- |
| Auth header | `authtoken: <ME_API_KEY>` | `Authorization: Zoho-oauthtoken <token>` |
| Base URL | `http(s)://host[:port]/api/v3` (portal optional) | `https://<region>.manageengine.com/app/<portal>/api/v3` |
| Accept header | `application/vnd.manageengine.sdp.v3+json` | `application/vnd.manageengine.sdp.v3+json` |

See the ManageEngine v3 change API documentation for [on-premises deployments](https://www.manageengine.com/products/service-desk/help/adminguide/apis/v3/change-api.html) and [cloud deployments](https://www.manageengine.com/products/service-desk/help/rest-api/change-api.html) for more details.

## CLI usage

Export ManageEngine changes to JSONL that is safe for LLM ingestion:

```bash
poetry run export-manageengine-llm \
  --status implemented \
  --from 2024-05-01T00:00:00 \
  --to 2024-05-07T23:59:59 \
  --out ./changes.jsonl
```

The command reads `ME_BASE_URL` and `ME_API_KEY` from the environment, fetches change events via the
ManageEngine client, performs deterministic redaction of emails, IPs, and tokens, and persists the
results as newline-delimited JSON.

## JSONL schema

Each exported record follows the canonical `ChangeEvent` model:

| Field | Type | Notes |
| --- | --- | --- |
| `id` | `str` | Provider identifier. |
| `submitted_at` | `datetime` | Creation timestamp in ISO 8601 format. |
| `implemented_at` | `datetime\|None` | Implementation timestamp, if available. |
| `service` | `str` | Service or system impacted by the change. |
| `requester` | `str` | Requester or owner of the change. |
| `risk` | `str\|None` | Provider risk classification. |
| `summary` | `str` | Short summary text (redacted). |
| `description` | `str` | Long-form description (redacted). |
| `approvals` | `list[Approval]` | Approval metadata with approver names redacted. |
| `diffs` | `list[ConfigDiff]` | Configuration deltas when provided. |
| `raw` | `dict[str, Any]` | Original provider payload for debugging. |

A richer example is available in `examples/export_me_llm.py` for programmatic use.

## Development

* Format and lint with `poetry run ruff format` and `poetry run ruff check`.
* Run mypy: `poetry run mypy`.
* Execute tests: `poetry run pytest`.
* Pre-commit hooks (ruff, mypy, pytest) enforce the same checks locally.

CI enforces formatting, linting, typing, and tests on every pull request via GitHub Actions.

## Roadmap

* Build first-class clients for Meraki, SolarWinds, Veeam, and DNS providers.
* Expand LLM preparation utilities with summarisation prompts and embeddings helpers.
* Provide shared ETL pipelines for additional infrastructure systems.
