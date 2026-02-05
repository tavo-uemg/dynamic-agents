"""Async repository responsible for CRUD operations on TeamModel rows."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models import TeamModel, TeamStatus
from ..schemas import TeamCreate, TeamUpdate
from .exceptions import AgentRepositoryError

__all__ = ["TeamRepository", "TeamRepositoryError"]


class TeamRepositoryError(AgentRepositoryError):
    """Raised when persistence operations for teams fail."""


class TeamRepository:
    """Lightweight data access layer for persisted team configurations."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def create(self, team_create: TeamCreate, user_id: UUID | None = None) -> TeamModel:
        """Create and persist a new team configuration."""

        payload = _config_to_model_data(team_create)
        if user_id is not None:
            payload["user_id"] = user_id

        model = TeamModel(**payload)
        try:
            async with self._session_factory() as session:
                session.add(model)
                await session.commit()
                await session.refresh(model)
                return model
        except SQLAlchemyError as exc:  # pragma: no cover - database errors
            raise TeamRepositoryError("Failed to create team") from exc

    async def get(self, team_id: UUID) -> TeamModel | None:
        """Return a single team by primary key."""

        try:
            async with self._session_factory() as session:
                return await session.get(TeamModel, team_id)
        except SQLAlchemyError as exc:  # pragma: no cover - database errors
            raise TeamRepositoryError("Failed to fetch team by id") from exc

    async def get_by_name(self, name: str, user_id: UUID | None = None) -> TeamModel | None:
        """Return the first team matching the provided name (scoped by user when provided)."""

        stmt = select(TeamModel).where(TeamModel.name == name)
        if user_id is not None:
            stmt = stmt.where(TeamModel.user_id == user_id)

        try:
            async with self._session_factory() as session:
                result = await session.execute(stmt.limit(1))
                return result.scalars().first()
        except SQLAlchemyError as exc:  # pragma: no cover - database errors
            raise TeamRepositoryError("Failed to fetch team by name") from exc

    async def list(
        self,
        user_id: UUID | None = None,
        tags: list[str] | None = None,
        status: TeamStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TeamModel]:
        """Return a filtered list of teams ordered by creation date."""

        stmt: Select[tuple[TeamModel]] = select(TeamModel)
        if user_id is not None:
            stmt = stmt.where(TeamModel.user_id == user_id)
        if status is not None:
            stmt = stmt.where(TeamModel.status == status)
        if tags:
            stmt = stmt.where(TeamModel.tags.contains(tags))

        stmt = stmt.order_by(TeamModel.created_at.desc()).offset(offset).limit(limit)

        try:
            async with self._session_factory() as session:
                result = await session.execute(stmt)
                return list(result.scalars().all())
        except SQLAlchemyError as exc:  # pragma: no cover - database errors
            raise TeamRepositoryError("Failed to list teams") from exc

    async def update(self, team_id: UUID, team_update: TeamUpdate) -> TeamModel | None:
        """Apply updates to an existing team configuration."""

        try:
            async with self._session_factory() as session:
                model = await session.get(TeamModel, team_id)
                if model is None:
                    return None

                self._apply_simple_updates(model, team_update)

                if team_update.llm_config is not None:
                    model.model_config = team_update.llm_config.model_dump(mode="json")
                if team_update.member_ids is not None:
                    model.member_ids = list(team_update.member_ids)
                if team_update.instructions is not None:
                    model.instructions = list(team_update.instructions)

                await session.commit()
                await session.refresh(model)
                return model
        except SQLAlchemyError as exc:  # pragma: no cover - database errors
            raise TeamRepositoryError("Failed to update team") from exc

    async def delete(self, team_id: UUID) -> bool:
        """Delete a team configuration by id; returns True when deleted."""

        try:
            async with self._session_factory() as session:
                model = await session.get(TeamModel, team_id)
                if model is None:
                    return False
                await session.delete(model)
                await session.commit()
                return True
        except SQLAlchemyError as exc:  # pragma: no cover - database errors
            raise TeamRepositoryError("Failed to delete team") from exc

    def _apply_simple_updates(self, model: TeamModel, team_update: TeamUpdate) -> None:
        mappings: dict[str, Any] = {
            "name": team_update.name,
            "description": team_update.description,
            "status": team_update.status,
            "respond_directly": team_update.respond_directly,
            "delegate_to_all_members": team_update.delegate_to_all_members,
            "share_member_interactions": team_update.share_member_interactions,
            "add_team_history_to_members": team_update.add_team_history_to_members,
            "num_team_history_runs": team_update.num_team_history_runs,
            "get_member_information_tool": team_update.get_member_information_tool,
            "store_member_responses": team_update.store_member_responses,
            "tags": team_update.tags,
        }

        for field, value in mappings.items():
            if value is not None:
                setattr(model, field, value)

        if team_update.metadata is not None:
            model.metadata_ = dict(team_update.metadata)


def _config_to_model_data(config: TeamCreate) -> dict[str, Any]:
    """Flatten a schema payload into a dict consumable by the ORM model."""

    data: dict[str, Any] = {
        "name": config.name,
        "description": config.description,
        "status": config.status,
        "model_config": config.model_config.model_dump(mode="json"),
        "member_ids": list(config.member_ids),
        "instructions": list(config.instructions),
        "respond_directly": config.respond_directly,
        "delegate_to_all_members": config.delegate_to_all_members,
        "share_member_interactions": config.share_member_interactions,
        "add_team_history_to_members": config.add_team_history_to_members,
        "num_team_history_runs": config.num_team_history_runs,
        "get_member_information_tool": config.get_member_information_tool,
        "store_member_responses": config.store_member_responses,
        "tags": list(config.tags),
        "metadata_": dict(config.metadata or {}),
        "user_id": config.user_id,
    }

    return data
