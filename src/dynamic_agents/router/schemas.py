"""Pydantic schemas used by the LiteLLM router manager."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ModelDeployment(BaseModel):
    """Concrete LiteLLM deployment description."""

    model_name: str
    litellm_params: dict[str, Any] = Field(default_factory=dict)
    model_info: dict[str, Any] | None = None

    def deployment_identifier(self) -> str:
        """Return a stable identifier for the deployment when available."""

        params_id = self.litellm_params.get("deployment_id")
        if isinstance(params_id, str) and params_id:
            return params_id
        alt_id = self.litellm_params.get("id")
        if isinstance(alt_id, str) and alt_id:
            return alt_id
        return self.model_name


class RouterHealthInfo(BaseModel):
    """Summary payload for router health endpoints."""

    initialized: bool
    routing_strategy: str
    total_deployments: int
    last_reload_at: datetime | None = None
    redis_enabled: bool = False
    redis_url: str | None = None
    allowed_fails: int
    cooldown_time: float
    num_retries: int
    tag_filtering_enabled: bool


__all__ = ["ModelDeployment", "RouterHealthInfo"]
