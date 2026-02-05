"""Agent ORM model and supporting enums."""

from __future__ import annotations

from enum import Enum
from typing import Any, TYPE_CHECKING

from sqlalchemy import Boolean, Enum as SqlEnum, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, JSONBType, TimestampMixin, UUIDPrimaryKey, UserOwnedMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .executions import ExecutionRecord


class AgentStatus(str, Enum):
    """Enumeration that captures the lifecycle of an agent configuration."""

    DRAFT = "draft"
    ACTIVE = "active"
    DISABLED = "disabled"


class AgentModel(UUIDPrimaryKey, TimestampMixin, UserOwnedMixin, Base):
    """Persistence model for dynamic agent configurations."""

    __tablename__ = "agents"
    __table_args__ = (
        Index("ix_agents_name", "name"),
        Index("ix_agents_user_id", "user_id"),
        Index("ix_agents_tags", "tags"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[AgentStatus] = mapped_column(
        SqlEnum(AgentStatus, name="agent_status"),
        default=AgentStatus.DRAFT,
        nullable=False,
    )

    system_message: Mapped[str | None] = mapped_column(Text())
    instructions: Mapped[list[str]] = mapped_column(JSONBType, default=list, nullable=False)
    expected_output: Mapped[str | None] = mapped_column(Text())
    additional_context: Mapped[str | None] = mapped_column(Text())

    markdown: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    add_datetime_to_context: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    add_location_to_context: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    add_name_to_context: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    enable_agentic_memory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enable_user_memories: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enable_session_summaries: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    add_history_to_context: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    num_history_runs: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    num_history_messages: Mapped[int] = mapped_column(Integer, default=20, nullable=False)

    tool_call_limit: Mapped[int | None] = mapped_column(Integer)
    show_tool_calls: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_chat_history: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    read_tool_call_history: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    output_schema: Mapped[str | None] = mapped_column(String(255))
    structured_outputs: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parse_response: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    use_json_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    reasoning: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reasoning_min_steps: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    reasoning_max_steps: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    model_config: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    reasoning_model_config: Mapped[dict[str, Any] | None] = mapped_column(JSONBType)
    knowledge_config: Mapped[dict[str, Any] | None] = mapped_column(JSONBType)

    tools: Mapped[list[dict[str, Any]]] = mapped_column(JSONBType, default=list, nullable=False)
    mcp_servers: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBType, default=list, nullable=False
    )
    tags: Mapped[list[str]] = mapped_column(JSONBType, default=list, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONBType,
        default=dict,
        nullable=False,
    )

    executions: Mapped[list["ExecutionRecord"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


__all__ = ["AgentModel", "AgentStatus"]
