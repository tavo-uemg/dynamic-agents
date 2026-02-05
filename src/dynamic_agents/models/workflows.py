"""Workflow ORM model definition."""

from __future__ import annotations

from enum import Enum
from typing import Any, TYPE_CHECKING

from sqlalchemy import Boolean, Enum as SqlEnum, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, JSONBType, TimestampMixin, UUIDPrimaryKey, UserOwnedMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .executions import ExecutionRecord


class WorkflowStatus(str, Enum):
    """States available for workflow definitions."""

    DRAFT = "draft"
    ACTIVE = "active"
    DISABLED = "disabled"


class WorkflowModel(UUIDPrimaryKey, TimestampMixin, UserOwnedMixin, Base):
    """Persistence model for workflow orchestration definitions."""

    __tablename__ = "workflows"
    __table_args__ = (
        Index("ix_workflows_name", "name"),
        Index("ix_workflows_user_id", "user_id"),
        Index("ix_workflows_tags", "tags"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    status: Mapped[WorkflowStatus] = mapped_column(
        SqlEnum(WorkflowStatus, name="workflow_status"),
        default=WorkflowStatus.DRAFT,
        nullable=False,
    )

    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSONBType, default=list, nullable=False)
    input_schema: Mapped[str | None] = mapped_column(Text())
    add_workflow_history_to_steps: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    stream_executor_events: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tags: Mapped[list[str]] = mapped_column(JSONBType, default=list, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONBType,
        default=dict,
        nullable=False,
    )

    executions: Mapped[list["ExecutionRecord"]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


__all__ = ["WorkflowModel", "WorkflowStatus"]
