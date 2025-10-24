from __future__ import annotations

from infraops_core.llm_prep import CHANGE_SUMMARY_TEMPLATE, chunk, redact


def test_redact_replaces_secrets_and_patterns() -> None:
    text = "User Alice email alice@example.com"
    result = redact(text, secrets=["Alice"], pii_patterns=[r"[\w.-]+@[\w.-]+"])
    assert "[REDACTED]" in result
    assert "example.com" not in result


def test_chunk_splits_records() -> None:
    records = ["a", "b", "c", "d"]
    batches = list(chunk(records, size=3))
    assert batches == [["a", "b", "c"], ["d"]]


def test_prompt_template_renders_context() -> None:
    rendered = CHANGE_SUMMARY_TEMPLATE.render(
        context={
            "summary": "Network change",
            "description": "Added VLAN",
        }
    )
    assert "Network change" in rendered["user"]
