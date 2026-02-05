"""Tool registry ORM model definitions."""

from __future__ import annotations

from enum import Enum
from typing import Any

from sqlalchemy import Boolean, Enum as SqlEnum, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, JSONBType, TimestampMixin, UUIDPrimaryKey, UserOwnedMixin


class ToolType(str, Enum):
    """Supported categories of tools."""

    BUILTIN = "builtin"
    FUNCTION = "function"
    MCP = "mcp"


class ToolStatus(str, Enum):
    """Lifecycle state for registered tools."""

    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


class MCPConnectionType(str, Enum):
    """Transport types supported by MCP servers."""

    COMMAND = "command"
    URL = "url"


class ToolModel(UUIDPrimaryKey, TimestampMixin, UserOwnedMixin, Base):
    """Registry row storing builtin, custom and MCP tool metadata."""

    __tablename__ = "tools"
    __table_args__ = (
        Index("ix_tools_name", "name"),
        Index("ix_tools_user_id", "user_id"),
        Index("ix_tools_tags", "tags"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    type: Mapped[ToolType] = mapped_column(
        SqlEnum(ToolType, name="tool_type"),
        default=ToolType.BUILTIN,
        nullable=False,
    )
    status: Mapped[ToolStatus] = mapped_column(
        SqlEnum(ToolStatus, name="tool_status"),
        default=ToolStatus.ACTIVE,
        nullable=False,
    )

    toolkit_name: Mapped[str | None] = mapped_column(String(255))
    toolkit_params: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)

    function_name: Mapped[str | None] = mapped_column(String(255))
    function_module: Mapped[str | None] = mapped_column(String(255))
    function_path: Mapped[str | None] = mapped_column(String(512))
    function_kwargs: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    timeout_seconds: Mapped[int | None] = mapped_column(Integer)

    mcp_connection_type: Mapped[MCPConnectionType | None] = mapped_column(
        SqlEnum(MCPConnectionType, name="mcp_connection_type"),
        nullable=True,
    )
    mcp_command: Mapped[str | None] = mapped_column(String(512))
    mcp_url: Mapped[str | None] = mapped_column(String(512))
    mcp_env: Mapped[dict[str, str]] = mapped_column(JSONBType, default=dict, nullable=False)
    mcp_tool_name_prefix: Mapped[str | None] = mapped_column(String(255))

    tags: Mapped[list[str]] = mapped_column(JSONBType, default=list, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONBType,
        default=dict,
        nullable=False,
    )
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


__all__ = [
    "MCPConnectionType",
    "ToolModel",
    "ToolStatus",
    "ToolType",
]
