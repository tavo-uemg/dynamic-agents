"""LiteLLM router schemas."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import ORMModel


class ModelConfig(ORMModel):
    """Request-level router model overrides."""

    model_name: str
    deployment_id: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    tags: list[str] = Field(default_factory=list)


class ModelDeployment(ORMModel):
    """Concrete LiteLLM deployment description."""

    model_name: str
    litellm_params: dict[str, Any]
    model_info: dict[str, Any] | None = None


class RouterConfig(ORMModel):
    """Schema for LiteLLM router configuration payloads."""

    model_list: list[ModelDeployment] = Field(default_factory=list)
    routing_strategy: str = "simple-shuffle"

    num_retries: int = 3
    timeout: float = 60.0
    allowed_fails: int = 3
    cooldown_time: float = 30.0

    fallbacks: dict[str, list[str]] = Field(default_factory=dict)
    default_fallbacks: list[str] = Field(default_factory=list)
    context_window_fallbacks: dict[str, list[str]] = Field(default_factory=dict)

    enable_pre_call_checks: bool = True
    enable_tag_filtering: bool = True
    cache_responses: bool = True

    redis_host: str | None = None
    redis_port: int | None = None
    redis_password: str | None = None


__all__ = ["ModelConfig", "ModelDeployment", "RouterConfig"]
