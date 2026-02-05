"""Reusable FastAPI dependency providers for the REST API layer."""

from __future__ import annotations

import logging
from typing import Annotated, AsyncGenerator

from fastapi import Depends
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.execution import ExecutionEngine
from ..core.factory import AgentFactory
from ..core.repository import AgentRepository
from ..core.team_repository import TeamRepository
from ..core.tool_registry import ToolRegistry
from ..router.config import RouterConfig as RouterSettings
from ..router.manager import RouterManager
from ..secrets.manager import SecretsManager
from ..storage.database import get_async_session, get_session_factory

logger = logging.getLogger(__name__)

_router_manager: RouterManager | None = None
_secrets_manager: SecretsManager | None = None
_secrets_manager_failed: bool = False
_tool_registry = ToolRegistry()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for request-scoped usage."""

    async with get_async_session() as session:
        yield session


def get_agent_repository() -> AgentRepository:
    """Return an AgentRepository bound to the global session factory."""

    return AgentRepository(get_session_factory())


def get_team_repository() -> TeamRepository:
    """Return a TeamRepository bound to the global session factory."""

    return TeamRepository(get_session_factory())


def get_secrets_manager() -> SecretsManager | None:
    """Lazily instantiate the SecretsManager when configuration is available."""

    global _secrets_manager, _secrets_manager_failed
    if _secrets_manager is not None or _secrets_manager_failed:
        return _secrets_manager
    try:
        _secrets_manager = SecretsManager()
    except ValidationError as exc:  # Missing env config is non-fatal for the API.
        logger.warning("SecretsManager disabled due to invalid configuration: %s", exc)
        _secrets_manager_failed = True
    return _secrets_manager


def get_router_manager() -> RouterManager:
    """Provide a singleton RouterManager instance."""

    global _router_manager
    if _router_manager is None:
        router_settings = RouterSettings()
        _router_manager = RouterManager(
            config=router_settings,
            secrets_manager=get_secrets_manager(),
        )
    return _router_manager


async def get_agent_factory(repo: AgentRepository = Depends(get_agent_repository)) -> AgentFactory:
    """Return an AgentFactory wired with router/secrets dependencies."""

    factory = AgentFactory(
        router_manager=get_router_manager(),
        secrets_manager=get_secrets_manager(),
        tool_registry=_tool_registry,
    )
    factory.bind_repository(repo)
    return factory


async def get_execution_engine(
    agent_factory: AgentFactory = Depends(get_agent_factory),
) -> ExecutionEngine:
    """Return an ExecutionEngine that can orchestrate agent runs."""

    return ExecutionEngine(
        agent_factory=agent_factory,
        session_factory=get_session_factory(),
    )


DbSession = Annotated[AsyncSession, Depends(get_db_session)]
AgentRepo = Annotated[AgentRepository, Depends(get_agent_repository)]
TeamRepo = Annotated[TeamRepository, Depends(get_team_repository)]
AgentFactoryDep = Annotated[AgentFactory, Depends(get_agent_factory)]
ExecutionEngineDep = Annotated[ExecutionEngine, Depends(get_execution_engine)]
RouterManagerDep = Annotated[RouterManager, Depends(get_router_manager)]


__all__ = [
    "AgentFactoryDep",
    "AgentRepo",
    "DbSession",
    "ExecutionEngineDep",
    "RouterManagerDep",
    "TeamRepo",
    "get_agent_factory",
    "get_agent_repository",
    "get_db_session",
    "get_execution_engine",
    "get_router_manager",
    "get_secrets_manager",
    "get_team_repository",
]
