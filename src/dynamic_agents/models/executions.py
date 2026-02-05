"""Execution history ORM model."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Enum as SqlEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, GUID, JSONBType, TimestampMixin, UUIDPrimaryKey, UserOwnedMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .agents import AgentModel
    from .router import RouterConfigModel
    from .teams import TeamModel
    from .workflows import WorkflowModel


class ExecutionTargetType(str, Enum):
    """Identifies the type of resource executed."""

    AGENT = "agent"
    TEAM = "team"
    WORKFLOW = "workflow"


class ExecutionStatus(str, Enum):
    """Lifecycle states for a run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionRecord(UUIDPrimaryKey, TimestampMixin, UserOwnedMixin, Base):
    """Historical record of agent/team/workflow executions."""

    __tablename__ = "executions"
    __table_args__ = (
        Index("ix_executions_status", "status"),
        Index("ix_executions_agent_id", "agent_id"),
        Index("ix_executions_team_id", "team_id"),
        Index("ix_executions_workflow_id", "workflow_id"),
        Index("ix_executions_user_id", "user_id"),
    )

    target_type: Mapped[ExecutionTargetType] = mapped_column(
        SqlEnum(ExecutionTargetType, name="execution_target_type"),
        nullable=False,
    )
    status: Mapped[ExecutionStatus] = mapped_column(
        SqlEnum(ExecutionStatus, name="execution_status"),
        default=ExecutionStatus.PENDING,
        nullable=False,
    )

    agent_id: Mapped[UUID | None] = mapped_column(
        GUID(),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    team_id: Mapped[UUID | None] = mapped_column(
        GUID(),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )
    workflow_id: Mapped[UUID | None] = mapped_column(
        GUID(),
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
    )
    router_config_id: Mapped[UUID | None] = mapped_column(
        GUID(),
        ForeignKey("router_configs.id", ondelete="SET NULL"),
        nullable=True,
    )

    session_id: Mapped[str | None] = mapped_column(String(255))
    request_id: Mapped[str | None] = mapped_column(String(255))

    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    output_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONBType)
    tool_calls: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBType, default=list, nullable=False
    )
    run_metadata: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)

    error_message: Mapped[str | None] = mapped_column(Text())
    duration_ms: Mapped[float | None] = mapped_column(Float)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    agent: Mapped["AgentModel | None"] = relationship(back_populates="executions")
    team: Mapped["TeamModel | None"] = relationship(back_populates="executions")
    workflow: Mapped["WorkflowModel | None"] = relationship(back_populates="executions")
    router_config: Mapped["RouterConfigModel | None"] = relationship(back_populates="executions")


__all__ = [
    "ExecutionRecord",
    "ExecutionStatus",
    "ExecutionTargetType",
]
