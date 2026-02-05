"""Utilities for converting between ORM models and agent schemas."""

from __future__ import annotations

from typing import Any

from ..models import AgentModel
from ..schemas import (
    AgentConfig,
    AgentCreate,
    KnowledgeConfig,
    MemorySettings,
    ModelConfig,
    OutputSettings,
    ReasoningSettings,
    ToolConfig,
)
from ..schemas.tools import MCPServerConfig
from .exceptions import AgentSerializationError

__all__ = ["model_to_config", "config_to_model_data"]


def model_to_config(model: AgentModel) -> AgentConfig:
    """Convert a persisted agent row into its schema representation."""

    try:
        memory = MemorySettings(
            enable_agentic_memory=model.enable_agentic_memory,
            enable_user_memories=model.enable_user_memories,
            enable_session_summaries=model.enable_session_summaries,
            add_history_to_context=model.add_history_to_context,
            add_name_to_context=model.add_name_to_context,
            add_datetime_to_context=model.add_datetime_to_context,
            add_location_to_context=model.add_location_to_context,
            num_history_runs=model.num_history_runs,
            num_history_messages=model.num_history_messages,
        )

        output = OutputSettings(
            output_schema=model.output_schema,
            structured_outputs=model.structured_outputs,
            parse_response=model.parse_response,
            use_json_mode=model.use_json_mode,
        )

        reasoning = ReasoningSettings(
            enabled=model.reasoning,
            min_steps=model.reasoning_min_steps,
            max_steps=model.reasoning_max_steps,
        )

        tools = model.tools or []
        mcp_servers = model.mcp_servers or []
        config_payload: dict[str, Any] = {
            "name": model.name,
            "description": model.description,
            "version": model.version,
            "status": model.status,
            "model_config": ModelConfig.model_validate(model.model_config),
            "reasoning_model_config": None,
            "system_message": model.system_message,
            "instructions": list(model.instructions or []),
            "expected_output": model.expected_output,
            "additional_context": model.additional_context,
            "memory": memory,
            "output": output,
            "reasoning": reasoning,
            "tools": [ToolConfig.model_validate(tool) for tool in tools],
            "mcp_servers": [MCPServerConfig.model_validate(server) for server in mcp_servers],
            "tool_call_limit": model.tool_call_limit,
            "show_tool_calls": model.show_tool_calls,
            "read_chat_history": model.read_chat_history,
            "read_tool_call_history": model.read_tool_call_history,
            "knowledge_config": None,
            "tags": list(model.tags or []),
            "metadata": dict(model.metadata_ or {}),
            "user_id": model.user_id,
        }

        if model.reasoning_model_config:
            config_payload["reasoning_model_config"] = ModelConfig.model_validate(
                model.reasoning_model_config
            )

        if model.knowledge_config:
            config_payload["knowledge_config"] = KnowledgeConfig.model_validate(
                model.knowledge_config
            )

        return AgentConfig(**config_payload)
    except Exception as exc:  # pragma: no cover - defensive
        raise AgentSerializationError("Failed to convert AgentModel to AgentConfig") from exc


def config_to_model_data(config: AgentCreate) -> dict[str, Any]:
    """Flatten a schema payload into a dict consumable by the ORM model."""

    try:
        memory = config.memory or MemorySettings()
        output = config.output or OutputSettings()
        reasoning = config.reasoning or ReasoningSettings()

        data: dict[str, Any] = {
            "name": config.name,
            "description": config.description,
            "version": config.version,
            "status": config.status,
            "system_message": config.system_message,
            "instructions": list(config.instructions),
            "expected_output": config.expected_output,
            "additional_context": config.additional_context,
            "enable_agentic_memory": memory.enable_agentic_memory,
            "enable_user_memories": memory.enable_user_memories,
            "enable_session_summaries": memory.enable_session_summaries,
            "add_history_to_context": memory.add_history_to_context,
            "add_name_to_context": memory.add_name_to_context,
            "add_datetime_to_context": memory.add_datetime_to_context,
            "add_location_to_context": memory.add_location_to_context,
            "num_history_runs": memory.num_history_runs,
            "num_history_messages": memory.num_history_messages,
            "tool_call_limit": config.tool_call_limit,
            "show_tool_calls": config.show_tool_calls,
            "read_chat_history": config.read_chat_history,
            "read_tool_call_history": config.read_tool_call_history,
            "model_config": config.model_config.model_dump(mode="json"),
            "reasoning_model_config": None,
            "knowledge_config": None,
            "output_schema": output.output_schema,
            "structured_outputs": output.structured_outputs,
            "parse_response": output.parse_response,
            "use_json_mode": output.use_json_mode,
            "reasoning": reasoning.enabled,
            "reasoning_min_steps": reasoning.min_steps,
            "reasoning_max_steps": reasoning.max_steps,
            "tools": [tool.model_dump(mode="json") for tool in config.tools],
            "mcp_servers": [server.model_dump(mode="json") for server in config.mcp_servers],
            "tags": list(config.tags),
            "metadata_": dict(config.metadata or {}),
            "user_id": config.user_id,
        }

        if config.reasoning_model_config:
            data["reasoning_model_config"] = config.reasoning_model_config.model_dump(mode="json")

        if config.knowledge_config:
            data["knowledge_config"] = config.knowledge_config.model_dump(mode="json")

        return data
    except Exception as exc:  # pragma: no cover - defensive
        raise AgentSerializationError("Failed to convert AgentCreate to model payload") from exc
