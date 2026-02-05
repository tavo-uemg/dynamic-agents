"""Factory that turns stored configurations into runnable Agno agents."""

from __future__ import annotations

import importlib
import logging
from typing import Any, Sequence
from uuid import UUID

from pydantic import BaseModel

from ..router import RouterManager
from ..schemas import AgentConfig, ToolConfig
from ..schemas.router import ModelConfig
from ..secrets import SecretsManager
from .exceptions import AgentFactoryError, AgentNotFoundError
from .repository import AgentRepository
from .serialization import model_to_config
from .tool_registry import ToolRegistry

__all__ = ["AgentFactory"]


class AgentFactory:
    """Assembles Agno agent instances using router, secrets and tool integrations."""

    def __init__(
        self,
        router_manager: RouterManager | None = None,
        secrets_manager: SecretsManager | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self._router_manager = router_manager
        self._secrets_manager = secrets_manager
        self._tool_registry = tool_registry or ToolRegistry()
        self._logger = logging.getLogger(__name__)
        self._default_repository: AgentRepository | None = None

    def bind_repository(self, repository: AgentRepository) -> None:
        """Store a default repository used by get_agent."""

        self._default_repository = repository

    async def get_agent(self, agent_id: UUID) -> Any:
        """Return a runnable agent for the stored identifier using the bound repository."""

        if self._default_repository is None:
            raise AgentFactoryError("AgentRepository has not been configured for this factory")
        return await self.create_from_id(agent_id, self._default_repository)

    async def create_from_config(self, config: AgentConfig) -> Any:
        """Create an Agno Agent instance from stored configuration."""

        agent_cls = self._require_agent_class()
        model_instance = await self._resolve_model(config.model_config)
        tools = await self._resolve_tools(config)
        output_schema = self._resolve_output_schema(config.output.output_schema)
        agent_kwargs = self._build_agent_kwargs(config, model_instance, tools, output_schema)

        try:
            agent = agent_cls(**agent_kwargs)
        except Exception as exc:  # pragma: no cover - instantiation errors
            raise AgentFactoryError("Failed to construct Agno Agent") from exc

        self._apply_runtime_settings(agent, config)
        return agent

    async def create_from_id(self, agent_id: UUID, repository: AgentRepository) -> Any:
        """Load config from repository and create agent."""

        model = await repository.get(agent_id)
        if model is None:
            raise AgentNotFoundError(f"Agent '{agent_id}' was not found")

        config = model_to_config(model)
        agent = await self.create_from_config(config)

        self._attach_identifiers(agent, agent_id, model.user_id)
        return agent

    async def _resolve_tools(self, config: AgentConfig) -> list[Any]:
        tool_configs: list[ToolConfig] = [tool.model_copy(deep=True) for tool in config.tools]
        for server in config.mcp_servers:
            tool_configs.append(ToolConfig(type="mcp", mcp_server=server))
        return await self._tool_registry.resolve_tools(tool_configs)

    async def _resolve_model(self, model_config: ModelConfig) -> Any:
        litellm_cls = self._load_litellm_class()
        payload = model_config.model_dump(exclude_none=True)
        model_name = payload.pop("model_name")

        router_kwargs: dict[str, Any] = {}
        if self._router_manager is not None:
            await self._router_manager.initialize()
            router_kwargs["router"] = self._router_manager.get_router()

        if litellm_cls is None:
            return model_name

        kwargs = {**payload, "id": model_name, **router_kwargs}
        try:
            return litellm_cls(**kwargs)
        except TypeError:
            self._logger.debug("LiteLLM rejected kwargs; falling back to bare id")
            return litellm_cls(id=model_name)

    def _resolve_output_schema(self, schema_path: str | None) -> type[BaseModel] | None:
        if not schema_path:
            return None

        normalized = schema_path.replace(":", ".")
        module_name, _, attr_name = normalized.rpartition(".")
        if not module_name or not attr_name:
            raise AgentFactoryError(
                "output_schema must be a dotted path in the form 'package.module.Schema'"
            )
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:  # pragma: no cover - import errors
            raise AgentFactoryError(f"Unable to import module '{module_name}'") from exc
        schema = getattr(module, attr_name, None)
        if not isinstance(schema, type) or not issubclass(schema, BaseModel):
            raise AgentFactoryError(f"Attribute '{attr_name}' is not a Pydantic model")
        return schema

    def _build_agent_kwargs(
        self,
        config: AgentConfig,
        model_instance: Any,
        tools: Sequence[Any],
        output_schema: type[BaseModel] | None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "name": config.name,
            "model": model_instance,
            "description": config.description,
            "system_message": config.system_message,
            "instructions": list(config.instructions),
            "tools": list(tools),
            "enable_agentic_memory": config.memory.enable_agentic_memory,
            "enable_user_memories": config.memory.enable_user_memories,
            "reasoning": config.reasoning.enabled,
            "reasoning_min_steps": config.reasoning.min_steps,
            "reasoning_max_steps": config.reasoning.max_steps,
            "structured_outputs": config.output.structured_outputs,
        }
        if output_schema is not None:
            kwargs["output_schema"] = output_schema
        if config.user_id is not None:
            kwargs["user_id"] = config.user_id
        return kwargs

    def _apply_runtime_settings(self, agent: Any, config: AgentConfig) -> None:
        agent.metadata = dict(config.metadata or {})
        agent.tags = list(config.tags)
        agent.tool_call_limit = config.tool_call_limit
        agent.show_tool_calls = config.show_tool_calls
        agent.read_chat_history = config.read_chat_history
        agent.read_tool_call_history = config.read_tool_call_history
        agent.expected_output = config.expected_output
        agent.additional_context = config.additional_context

        memory = config.memory
        agent.enable_session_summaries = memory.enable_session_summaries
        agent.add_history_to_context = memory.add_history_to_context
        agent.add_name_to_context = memory.add_name_to_context
        agent.add_datetime_to_context = memory.add_datetime_to_context
        agent.add_location_to_context = memory.add_location_to_context
        agent.num_history_runs = memory.num_history_runs
        agent.num_history_messages = memory.num_history_messages

        output = config.output
        agent.parse_response = output.parse_response
        agent.use_json_mode = output.use_json_mode
        agent.output_schema_name = output.output_schema

        if config.reasoning_model_config is not None:
            agent.reasoning_model_config = config.reasoning_model_config.model_dump(mode="json")
        if config.knowledge_config is not None:
            agent.knowledge_config = config.knowledge_config.model_dump(mode="json")

        agent.mcp_servers = [server.model_dump(mode="json") for server in config.mcp_servers]
        agent.tools_config = [tool.model_dump(mode="json") for tool in config.tools]
        agent.router_manager = self._router_manager
        agent.secrets_manager = self._secrets_manager
        agent.tool_registry = self._tool_registry

    def _attach_identifiers(self, agent: Any, agent_id: UUID, user_id: UUID | None) -> None:
        setattr(agent, "id", agent_id)
        if user_id is not None:
            setattr(agent, "user_id", user_id)

    def _require_agent_class(self) -> type[Any]:
        try:  # pragma: no cover - optional dependency
            from agno.agent import Agent as AgnoAgent  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise AgentFactoryError(
                "agno is not installed; install 'dynamic-agents[all]' to create agents"
            ) from exc
        return AgnoAgent

    def _load_litellm_class(self) -> type[Any] | None:
        try:  # pragma: no cover - optional dependency
            from agno.models.litellm import LiteLLM  # type: ignore
        except Exception:  # pragma: no cover - optional dependency
            return None
        return LiteLLM
