"""Workflow schema definitions."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from ..models import WorkflowStatus
from .base import IdentifiedSchema, ORMModel


class StepConfig(ORMModel):
    """Representation of a workflow step definition."""

    name: str
    type: Literal["agent", "team", "parallel", "condition", "loop"]
    executor_id: str | None = None
    parallel_steps: list["StepConfig"] | None = None
    condition: str | None = None
    loop_condition: str | None = None


class WorkflowConfigBase(ORMModel):
    """Shared workflow configuration payload."""

    name: str
    description: str | None = None
    status: WorkflowStatus = WorkflowStatus.DRAFT
    steps: list[StepConfig] = Field(default_factory=list)
    input_schema: str | None = None
    add_workflow_history_to_steps: bool = False
    stream_executor_events: bool = True
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowConfig(WorkflowConfigBase):
    """Stored workflow config representation."""

    user_id: UUID | None = None


class WorkflowCreate(WorkflowConfigBase):
    """Creation payload for workflows."""

    user_id: UUID | None = None


class WorkflowUpdate(ORMModel):
    """Partial update payload for workflows."""

    name: str | None = None
    description: str | None = None
    status: WorkflowStatus | None = None
    steps: list[StepConfig] | None = None
    input_schema: str | None = None
    add_workflow_history_to_steps: bool | None = None
    stream_executor_events: bool | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class WorkflowResponse(IdentifiedSchema, WorkflowConfigBase):
    """Response payload for persisted workflows."""

    user_id: UUID | None = None


StepConfig.model_rebuild()


__all__ = [
    "StepConfig",
    "WorkflowConfig",
    "WorkflowCreate",
    "WorkflowResponse",
    "WorkflowUpdate",
]
