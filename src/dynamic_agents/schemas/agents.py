"""Agent schema definitions."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field

from ..models import AgentStatus
from .base import IdentifiedSchema, ORMModel
from .router import ModelConfig
from .tools import MCPServerConfig, ToolConfig


class MemorySettings(ORMModel):
    """Fine-grained control over history and memory behaviour."""

    enable_agentic_memory: bool = False
    enable_user_memories: bool = False
    enable_session_summaries: bool = False
    add_history_to_context: bool = True
    add_name_to_context: bool = False
    add_datetime_to_context: bool = False
    add_location_to_context: bool = False
    num_history_runs: int = 3
    num_history_messages: int = 20


class OutputSettings(ORMModel):
    """Schema describing output parsing behaviour."""

    output_schema: str | None = None
    structured_outputs: bool = False
    parse_response: bool = False
    use_json_mode: bool = False


class ReasoningSettings(ORMModel):
    """Reasoning configuration for complex models."""

    enabled: bool = False
    min_steps: int = 1
    max_steps: int = 10


class KnowledgeConfig(ORMModel):
    """RAG and knowledge base controls."""

    enabled: bool = False
    vector_store: str | None = None
    collection: str | None = None
    search_knowledge: bool = False
    filters: dict[str, Any] = Field(default_factory=dict)
    retriever: dict[str, Any] = Field(default_factory=dict)


class AgentConfigBase(ORMModel):
    """Shared payload for agent-config-like schemas."""

    name: str
    description: str | None = None
    version: int = 1
    status: AgentStatus = AgentStatus.DRAFT

    model_config: ModelConfig
    reasoning_model_config: ModelConfig | None = None

    system_message: str | None = None
    instructions: list[str] = Field(default_factory=list)
    expected_output: str | None = None
    additional_context: str | None = None

    memory: MemorySettings = Field(default_factory=MemorySettings)
    output: OutputSettings = Field(default_factory=OutputSettings)
    reasoning: ReasoningSettings = Field(default_factory=ReasoningSettings)

    tools: list[ToolConfig] = Field(default_factory=list)
    mcp_servers: list[MCPServerConfig] = Field(default_factory=list)
    tool_call_limit: int | None = None
    show_tool_calls: bool = False
    read_chat_history: bool = True
    read_tool_call_history: bool = True

    knowledge_config: KnowledgeConfig | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentConfig(AgentConfigBase):
    """Agent configuration as stored in persistence layer."""

    user_id: UUID | None = None


class AgentCreate(AgentConfigBase):
    """Payload to create a new agent."""

    user_id: UUID | None = None


class AgentUpdate(ORMModel):
    """Partial update payload for agents."""

    name: str | None = None
    description: str | None = None
    version: int | None = None
    status: AgentStatus | None = None
    model_config: ModelConfig | None = None
    reasoning_model_config: ModelConfig | None = None
    system_message: str | None = None
    instructions: list[str] | None = None
    expected_output: str | None = None
    additional_context: str | None = None
    memory: MemorySettings | None = None
    output: OutputSettings | None = None
    reasoning: ReasoningSettings | None = None
    tools: list[ToolConfig] | None = None
    mcp_servers: list[MCPServerConfig] | None = None
    tool_call_limit: int | None = None
    show_tool_calls: bool | None = None
    read_chat_history: bool | None = None
    read_tool_call_history: bool | None = None
    knowledge_config: KnowledgeConfig | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class AgentResponse(IdentifiedSchema, AgentConfigBase):
    """Response schema for returning stored agents."""

    user_id: UUID | None = None


__all__ = [
    "AgentConfig",
    "AgentConfigBase",
    "AgentCreate",
    "AgentResponse",
    "AgentUpdate",
    "KnowledgeConfig",
    "MemorySettings",
    "OutputSettings",
    "ReasoningSettings",
]
