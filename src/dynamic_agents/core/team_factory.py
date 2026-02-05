"""Factory that turns stored team configurations into runnable Agno teams."""

from __future__ import annotations

import logging
from typing import Any, Sequence
from uuid import UUID

from ..models import TeamModel
from ..router import RouterManager
from ..schemas import TeamConfig
from ..schemas.router import ModelConfig
from .exceptions import AgentFactoryError, AgentNotFoundError
from .factory import AgentFactory
from .team_repository import TeamRepository

__all__ = ["TeamFactory", "TeamFactoryError", "TeamNotFoundError"]


class TeamFactoryError(AgentFactoryError):
    """Raised when a team cannot be assembled or configured."""


class TeamNotFoundError(TeamFactoryError, AgentNotFoundError):
    """Raised when a requested team configuration cannot be located."""


class TeamFactory:
    """Assembles Agno team instances with resolved member agents."""

    def __init__(
        self,
        agent_factory: AgentFactory,
        router_manager: RouterManager | None = None,
    ) -> None:
        self._agent_factory = agent_factory
        self._router_manager = router_manager
        self._logger = logging.getLogger(__name__)
        self._default_repository: TeamRepository | None = None

    def bind_repository(self, repository: TeamRepository) -> None:
        """Store a default repository used by get_team."""

        self._default_repository = repository

    async def get_team(self, team_id: UUID) -> Any:
        """Return a runnable team for the stored identifier using the bound repository."""

        if self._default_repository is None:
            raise TeamFactoryError("TeamRepository has not been configured for this factory")
        return await self.create_from_id(team_id, self._default_repository)

    async def create_from_config(self, config: TeamConfig) -> Any:
        """Create an Agno Team instance from stored configuration."""

        team_cls = self._require_team_class()
        model_instance = await self._resolve_model(config.llm_config)
        members = await self._resolve_members(config.member_ids)
        team_kwargs = self._build_team_kwargs(config, model_instance, members)

        try:
            team = team_cls(**team_kwargs)
        except Exception as exc:  # pragma: no cover - instantiation errors
            raise TeamFactoryError("Failed to construct Agno Team") from exc

        self._apply_runtime_settings(team, config)
        return team

    async def create_from_id(self, team_id: UUID, repository: TeamRepository) -> Any:
        """Load config from repository and create team."""

        model = await repository.get(team_id)
        if model is None:
            raise TeamNotFoundError(f"Team '{team_id}' was not found")

        config = _model_to_team_config(model)
        team = await self.create_from_config(config)

        self._attach_identifiers(team, team_id, model.user_id)
        return team

    async def _resolve_members(self, member_ids: Sequence[str]) -> list[Any]:
        if not member_ids:
            return []
        if self._agent_factory is None:
            raise TeamFactoryError("AgentFactory is required to resolve team members")

        members = []
        for raw_id in member_ids:
            try:
                member_uuid = UUID(raw_id)
            except (TypeError, ValueError) as exc:
                raise TeamFactoryError(f"Member id '{raw_id}' is not a valid UUID") from exc

            agent = await self._agent_factory.get_agent(member_uuid)
            members.append(agent)
        return members

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

    def _build_team_kwargs(
        self,
        config: TeamConfig,
        model_instance: Any,
        members: Sequence[Any],
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "name": config.name,
            "model": model_instance,
            "description": config.description,
            "members": list(members),
            "instructions": list(config.instructions),
            "respond_directly": config.respond_directly,
            "delegate_to_all_members": config.delegate_to_all_members,
            "share_member_interactions": config.share_member_interactions,
            "add_team_history_to_members": config.add_team_history_to_members,
            "num_team_history_runs": config.num_team_history_runs,
            "get_member_information_tool": config.get_member_information_tool,
            "store_member_responses": config.store_member_responses,
        }
        if config.user_id is not None:
            kwargs["user_id"] = config.user_id
        return kwargs

    def _apply_runtime_settings(self, team: Any, config: TeamConfig) -> None:
        team.metadata = dict(config.metadata or {})
        team.tags = list(config.tags)
        team.member_ids = list(config.member_ids)

    def _attach_identifiers(self, team: Any, team_id: UUID, user_id: UUID | None) -> None:
        setattr(team, "id", team_id)
        if user_id is not None:
            setattr(team, "user_id", user_id)

    def _require_team_class(self) -> type[Any]:
        try:  # pragma: no cover - optional dependency
            from agno.team import Team as AgnoTeam  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise TeamFactoryError(
                "agno is not installed; install 'dynamic-agents[all]' to create teams"
            ) from exc
        return AgnoTeam

    def _load_litellm_class(self) -> type[Any] | None:
        try:  # pragma: no cover - optional dependency
            from agno.models.litellm import LiteLLM  # type: ignore
        except Exception:  # pragma: no cover - optional dependency
            return None
        return LiteLLM


def _model_to_team_config(model: TeamModel) -> TeamConfig:
    payload = {
        "name": model.name,
        "description": model.description,
        "status": model.status,
        "model_config": ModelConfig.model_validate(model.model_config),
        "member_ids": list(model.member_ids or []),
        "instructions": list(model.instructions or []),
        "respond_directly": model.respond_directly,
        "delegate_to_all_members": model.delegate_to_all_members,
        "share_member_interactions": model.share_member_interactions,
        "add_team_history_to_members": model.add_team_history_to_members,
        "num_team_history_runs": model.num_team_history_runs,
        "get_member_information_tool": model.get_member_information_tool,
        "store_member_responses": model.store_member_responses,
        "tags": list(model.tags or []),
        "metadata": dict(model.metadata_ or {}),
        "user_id": model.user_id,
    }

    return TeamConfig(**payload)
