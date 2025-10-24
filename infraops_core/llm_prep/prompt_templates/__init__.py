"""Prompt templates for InfraOps LLM workflows."""

from infraops_core.llm_prep.prompt_templates.base import PromptTemplate

CHANGE_SUMMARY_TEMPLATE = PromptTemplate(
    system="You summarize infrastructure change events for audit teams.",
    user=(
        "Summarize the following change with emphasis on risk and implementation details:\n"
        "Summary: {summary}\n"
        "Description: {description}\n"
    ),
)

__all__ = ["PromptTemplate", "CHANGE_SUMMARY_TEMPLATE"]
