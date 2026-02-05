"""Async repository responsible for CRUD operations on AgentModel rows."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models import AgentModel, AgentStatus
from ..schemas import AgentCreate, AgentUpdate
from .exceptions import AgentRepositoryError
from .serialization import config_to_model_data

__all__ = ["AgentRepository"]


class AgentRepository:
    """Lightweight data access layer for persisted agent configurations."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def create(self, agent_create: AgentCreate, user_id: UUID | None = None) -> AgentModel:
        """Create and persist a new agent configuration."""

        payload = config_to_model_data(agent_create)
        if user_id is not None:
            payload["user_id"] = user_id

        model = AgentModel(**payload)
        try:
            async with self._session_factory() as session:
                session.add(model)
                await session.commit()
                await session.refresh(model)
                return model
        except SQLAlchemyError as exc:  # pragma: no cover - database errors
            raise AgentRepositoryError("Failed to create agent") from exc

    async def get(self, agent_id: UUID) -> AgentModel | None:
        """Return a single agent by primary key."""

        try:
            async with self._session_factory() as session:
                return await session.get(AgentModel, agent_id)
        except SQLAlchemyError as exc:  # pragma: no cover - database errors
            raise AgentRepositoryError("Failed to fetch agent by id") from exc

    async def get_by_name(self, name: str, user_id: UUID | None = None) -> AgentModel | None:
        """Return the first agent matching the provided name (scoped by user when provided)."""

        stmt = select(AgentModel).where(AgentModel.name == name)
        if user_id is not None:
            stmt = stmt.where(AgentModel.user_id == user_id)

        try:
            async with self._session_factory() as session:
                result = await session.execute(stmt.limit(1))
                return result.scalars().first()
        except SQLAlchemyError as exc:  # pragma: no cover - database errors
            raise AgentRepositoryError("Failed to fetch agent by name") from exc

    async def list(
        self,
        user_id: UUID | None = None,
        tags: list[str] | None = None,
        status: AgentStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AgentModel]:
        """Return a filtered list of agents ordered by creation date."""

        stmt: Select[tuple[AgentModel]] = select(AgentModel)
        if user_id is not None:
            stmt = stmt.where(AgentModel.user_id == user_id)
        if status is not None:
            stmt = stmt.where(AgentModel.status == status)
        if tags:
            stmt = stmt.where(AgentModel.tags.contains(tags))

        stmt = stmt.order_by(AgentModel.created_at.desc()).offset(offset).limit(limit)

        try:
            async with self._session_factory() as session:
                result = await session.execute(stmt)
                return list(result.scalars().all())
        except SQLAlchemyError as exc:  # pragma: no cover - database errors
            raise AgentRepositoryError("Failed to list agents") from exc

    async def update(self, agent_id: UUID, agent_update: AgentUpdate) -> AgentModel | None:
        """Apply updates to an existing agent configuration."""

        try:
            async with self._session_factory() as session:
                model = await session.get(AgentModel, agent_id)
                if model is None:
                    return None

                self._apply_simple_updates(model, agent_update)

                if agent_update.llm_config is not None:
                    model.model_config = agent_update.llm_config.model_dump(mode="json")
                if agent_update.reasoning_llm_config is not None:
                    model.reasoning_model_config = agent_update.reasoning_llm_config.model_dump(
                        mode="json"
                    )
                if agent_update.memory is not None:
                    mem = agent_update.memory
                    model.enable_agentic_memory = mem.enable_agentic_memory
                    model.enable_user_memories = mem.enable_user_memories
                    model.enable_session_summaries = mem.enable_session_summaries
                    model.add_history_to_context = mem.add_history_to_context
                    model.add_name_to_context = mem.add_name_to_context
                    model.add_datetime_to_context = mem.add_datetime_to_context
                    model.add_location_to_context = mem.add_location_to_context
                    model.num_history_runs = mem.num_history_runs
                    model.num_history_messages = mem.num_history_messages
                if agent_update.output is not None:
                    output = agent_update.output
                    model.output_schema = output.output_schema
                    model.structured_outputs = output.structured_outputs
                    model.parse_response = output.parse_response
                    model.use_json_mode = output.use_json_mode
                if agent_update.reasoning is not None:
                    reasoning = agent_update.reasoning
                    model.reasoning = reasoning.enabled
                    model.reasoning_min_steps = reasoning.min_steps
                    model.reasoning_max_steps = reasoning.max_steps
                if agent_update.tools is not None:
                    model.tools = [tool.model_dump(mode="json") for tool in agent_update.tools]
                if agent_update.mcp_servers is not None:
                    model.mcp_servers = [
                        server.model_dump(mode="json") for server in agent_update.mcp_servers
                    ]
                if agent_update.knowledge_config is not None:
                    model.knowledge_config = agent_update.knowledge_config.model_dump(mode="json")

                await session.commit()
                await session.refresh(model)
                return model
        except SQLAlchemyError as exc:  # pragma: no cover - database errors
            raise AgentRepositoryError("Failed to update agent") from exc

    async def delete(self, agent_id: UUID) -> bool:
        """Delete an agent configuration by id; returns True when deleted."""

        try:
            async with self._session_factory() as session:
                model = await session.get(AgentModel, agent_id)
                if model is None:
                    return False
                await session.delete(model)
                await session.commit()
                return True
        except SQLAlchemyError as exc:  # pragma: no cover - database errors
            raise AgentRepositoryError("Failed to delete agent") from exc

    async def increment_version(self, agent_id: UUID) -> AgentModel | None:
        """Atomically increment the stored version field."""

        try:
            async with self._session_factory() as session:
                model = await session.get(AgentModel, agent_id)
                if model is None:
                    return None
                model.version += 1
                await session.commit()
                await session.refresh(model)
                return model
        except SQLAlchemyError as exc:  # pragma: no cover - database errors
            raise AgentRepositoryError("Failed to increment agent version") from exc

    def _apply_simple_updates(self, model: AgentModel, agent_update: AgentUpdate) -> None:
        mappings: dict[str, Any] = {
            "name": agent_update.name,
            "description": agent_update.description,
            "version": agent_update.version,
            "status": agent_update.status,
            "system_message": agent_update.system_message,
            "instructions": agent_update.instructions,
            "expected_output": agent_update.expected_output,
            "additional_context": agent_update.additional_context,
            "tool_call_limit": agent_update.tool_call_limit,
            "show_tool_calls": agent_update.show_tool_calls,
            "read_chat_history": agent_update.read_chat_history,
            "read_tool_call_history": agent_update.read_tool_call_history,
            "tags": agent_update.tags,
        }

        for field, value in mappings.items():
            if value is not None:
                setattr(model, field, value)

        if agent_update.metadata is not None:
            model.metadata_ = dict(agent_update.metadata)
