"""Tool schema definitions."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from .base import ORMModel


class MCPServerConfig(ORMModel):
    """Configuration block for Model Context Protocol servers."""

    connection_type: Literal["command", "url"]
    command: str | None = None
    url: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    tool_name_prefix: str | None = None


class ToolConfig(ORMModel):
    """Schema describing builtin, custom or MCP tools."""

    type: Literal["builtin", "function", "mcp"]
    toolkit_name: str | None = None
    toolkit_params: dict[str, Any] = Field(default_factory=dict)

    function_name: str | None = None
    function_module: str | None = None
    function_path: str | None = None
    timeout_seconds: int | None = None

    mcp_server: MCPServerConfig | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = ["MCPServerConfig", "ToolConfig"]
