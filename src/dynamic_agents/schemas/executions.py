"""Execution schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from ..models import ExecutionStatus, ExecutionTargetType
from .base import IdentifiedSchema, ORMModel


class RunOutput(ORMModel):
    """Represents the immediate output of a single execution run."""

    execution_id: UUID
    status: ExecutionStatus
    output: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class ExecutionResult(IdentifiedSchema):
    """Full execution record returned by persistence layer."""

    target_type: ExecutionTargetType
    status: ExecutionStatus
    agent_id: UUID | None = None
    team_id: UUID | None = None
    workflow_id: UUID | None = None
    router_config_id: UUID | None = None
    session_id: str | None = None
    request_id: str | None = None

    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    run_metadata: dict[str, Any] = Field(default_factory=dict)

    error_message: str | None = None
    duration_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


__all__ = ["ExecutionResult", "RunOutput"]
