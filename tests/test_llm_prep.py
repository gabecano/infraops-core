from __future__ import annotations

from infraops_core.llm_prep import CHANGE_SUMMARY_TEMPLATE, chunk_text, redact


def test_redact_replaces_ips_tokens_and_emails() -> None:
    text = "Admin key=ABCDEF1234567890abcdef user alice@example.com from 192.168.1.10"
    result = redact(text, secrets=["Admin"], extra_patterns=[r"key="])
    assert result.count("[REDACTED]") >= 3
    assert "example.com" not in result
    assert "192.168.1.10" not in result
    assert "ABCDEF" not in result


def test_chunk_text_respects_boundaries_and_overlap() -> None:
    text = "abcdefghij"  # 10 chars
    chunks = list(chunk_text(text, size=4, overlap=1))
    assert chunks == ["abcd", "defg", "ghij"]


def test_chunk_text_empty() -> None:
    assert list(chunk_text("", size=5)) == []


def test_prompt_template_renders_context() -> None:
    rendered = CHANGE_SUMMARY_TEMPLATE.render(
        context={
            "summary": "Network change",
            "description": "Added VLAN",
        }
    )
    assert "Network change" in rendered["user"]
