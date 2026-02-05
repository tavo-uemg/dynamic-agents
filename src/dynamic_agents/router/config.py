"""Pydantic settings for configuring the LiteLLM router."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings

from .schemas import ModelDeployment


class RouterConfig(BaseSettings):
    """Runtime configuration for the LiteLLM router."""

    model_list: list[ModelDeployment] = Field(default_factory=list)
    routing_strategy: str = "usage-based-routing-v2"
    num_retries: int = 3
    fallbacks: dict[str, list[str]] = Field(default_factory=dict)
    default_fallbacks: list[str] = Field(default_factory=list)
    context_window_fallbacks: dict[str, list[str]] = Field(default_factory=dict)
    allowed_fails: int = 3
    cooldown_time: float = 30.0
    enable_pre_call_checks: bool = True
    enable_tag_filtering: bool = True

    redis_host: str | None = None
    redis_port: int = 6379
    redis_password: str | None = None
    redis_url: str | None = None

    model_config = BaseSettings.model_config.copy()
    model_config.update(
        {
            "env_prefix": "LITELLM_",
            "env_nested_delimiter": "__",
        }
    )


__all__ = ["RouterConfig"]
