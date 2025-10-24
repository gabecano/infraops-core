"""Configuration helpers for InfraOps Core."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Mapping

from dotenv import load_dotenv
from pydantic import BaseModel, Field, HttpUrl, ValidationError

load_dotenv()


class Settings(BaseModel):
    """Typed application settings derived from environment variables."""

    manageengine_base_url: HttpUrl | None = Field(
        default=None,
        description="Base URL for the ManageEngine ServiceDesk Plus API.",
    )
    manageengine_api_key: str | None = Field(
        default=None,
        description="Technician API key used to authenticate ManageEngine API requests.",
    )
    default_request_timeout: float = Field(
        default=30.0,
        ge=0,
        description="Default timeout (in seconds) for HTTP requests issued by the shared clients.",
    )
    max_retry_attempts: int = Field(
        default=5,
        ge=0,
        description="Maximum retry attempts applied by the shared HTTP retry logic.",
    )
    retry_backoff_seconds: float = Field(
        default=1.0,
        ge=0,
        description="Initial backoff delay (in seconds) used for exponential retry strategies.",
    )

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        """Create settings from environment variables.

        Args:
            env: Optional mapping used instead of :data:`os.environ` for testing.

        Returns:
            A validated :class:`Settings` instance.
        """

        data: dict[str, Any] = {}
        source = env or os.environ

        if "MANAGEENGINE_BASE_URL" in source:
            data["manageengine_base_url"] = source["MANAGEENGINE_BASE_URL"]
        if "MANAGEENGINE_API_KEY" in source:
            data["manageengine_api_key"] = source["MANAGEENGINE_API_KEY"]
        if "INFRAOPS_DEFAULT_TIMEOUT" in source:
            data["default_request_timeout"] = source["INFRAOPS_DEFAULT_TIMEOUT"]
        if "INFRAOPS_MAX_RETRIES" in source:
            data["max_retry_attempts"] = source["INFRAOPS_MAX_RETRIES"]
        if "INFRAOPS_RETRY_BACKOFF" in source:
            data["retry_backoff_seconds"] = source["INFRAOPS_RETRY_BACKOFF"]

        try:
            return cls(**data)
        except ValidationError as exc:  # pragma: no cover - defensive guard
            raise RuntimeError("Invalid InfraOps configuration") from exc


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance constructed from the environment."""

    return Settings.from_env()


__all__ = ["Settings", "get_settings"]
