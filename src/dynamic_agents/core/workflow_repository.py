"""Async repository responsible for CRUD operations on WorkflowModel rows."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models import WorkflowModel, WorkflowStatus
from ..schemas import WorkflowCreate, WorkflowUpdate
from ..schemas.workflows import StepConfig
from .exceptions import AgentRepositoryError

__all__ = ["WorkflowRepository", "WorkflowRepositoryError"]


class WorkflowRepositoryError(AgentRepositoryError):
    """Raised when persistence operations for workflows fail."""


class WorkflowRepository:
    """Lightweight data access layer for persisted workflow configurations."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def create(
        self,
        workflow_create: WorkflowCreate,
        user_id: UUID | None = None,
    ) -> WorkflowModel:
        """Create and persist a new workflow configuration."""

        payload = _config_to_model_data(workflow_create)
        if user_id is not None:
            payload["user_id"] = user_id

        model = WorkflowModel(**payload)
        try:
            async with self._session_factory() as session:
                session.add(model)
                await session.commit()
                await session.refresh(model)
                return model
        except SQLAlchemyError as exc:  # pragma: no cover - database errors
            raise WorkflowRepositoryError("Failed to create workflow") from exc

    async def get(self, workflow_id: UUID) -> WorkflowModel | None:
        """Return a single workflow by primary key."""

        try:
            async with self._session_factory() as session:
                return await session.get(WorkflowModel, workflow_id)
        except SQLAlchemyError as exc:  # pragma: no cover - database errors
            raise WorkflowRepositoryError("Failed to fetch workflow by id") from exc

    async def get_by_name(
        self,
        name: str,
        user_id: UUID | None = None,
    ) -> WorkflowModel | None:
        """Return the first workflow matching the provided name (scoped by user when provided)."""

        stmt = select(WorkflowModel).where(WorkflowModel.name == name)
        if user_id is not None:
            stmt = stmt.where(WorkflowModel.user_id == user_id)

        try:
            async with self._session_factory() as session:
                result = await session.execute(stmt.limit(1))
                return result.scalars().first()
        except SQLAlchemyError as exc:  # pragma: no cover - database errors
            raise WorkflowRepositoryError("Failed to fetch workflow by name") from exc

    async def list(
        self,
        user_id: UUID | None = None,
        tags: list[str] | None = None,
        status: WorkflowStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorkflowModel]:
        """Return a filtered list of workflows ordered by creation date."""

        stmt: Select[tuple[WorkflowModel]] = select(WorkflowModel)
        if user_id is not None:
            stmt = stmt.where(WorkflowModel.user_id == user_id)
        if status is not None:
            stmt = stmt.where(WorkflowModel.status == status)
        if tags:
            stmt = stmt.where(WorkflowModel.tags.contains(tags))

        stmt = stmt.order_by(WorkflowModel.created_at.desc()).offset(offset).limit(limit)

        try:
            async with self._session_factory() as session:
                result = await session.execute(stmt)
                return list(result.scalars().all())
        except SQLAlchemyError as exc:  # pragma: no cover - database errors
            raise WorkflowRepositoryError("Failed to list workflows") from exc

    async def update(
        self,
        workflow_id: UUID,
        workflow_update: WorkflowUpdate,
    ) -> WorkflowModel | None:
        """Apply updates to an existing workflow configuration."""

        try:
            async with self._session_factory() as session:
                model = await session.get(WorkflowModel, workflow_id)
                if model is None:
                    return None

                self._apply_simple_updates(model, workflow_update)

                if workflow_update.steps is not None:
                    model.steps = _steps_to_payload(workflow_update.steps)
                if workflow_update.tags is not None:
                    model.tags = list(workflow_update.tags)
                if workflow_update.metadata is not None:
                    model.metadata_ = dict(workflow_update.metadata)

                await session.commit()
                await session.refresh(model)
                return model
        except SQLAlchemyError as exc:  # pragma: no cover - database errors
            raise WorkflowRepositoryError("Failed to update workflow") from exc

    async def delete(self, workflow_id: UUID) -> bool:
        """Delete a workflow configuration by id; returns True when deleted."""

        try:
            async with self._session_factory() as session:
                model = await session.get(WorkflowModel, workflow_id)
                if model is None:
                    return False
                await session.delete(model)
                await session.commit()
                return True
        except SQLAlchemyError as exc:  # pragma: no cover - database errors
            raise WorkflowRepositoryError("Failed to delete workflow") from exc

    def _apply_simple_updates(
        self,
        model: WorkflowModel,
        workflow_update: WorkflowUpdate,
    ) -> None:
        mappings: dict[str, Any] = {
            "name": workflow_update.name,
            "description": workflow_update.description,
            "status": workflow_update.status,
            "input_schema": workflow_update.input_schema,
            "add_workflow_history_to_steps": workflow_update.add_workflow_history_to_steps,
            "stream_executor_events": workflow_update.stream_executor_events,
        }

        for field, value in mappings.items():
            if value is not None:
                setattr(model, field, value)


def _config_to_model_data(config: WorkflowCreate) -> dict[str, Any]:
    """Flatten a schema payload into a dict consumable by the ORM model."""

    data: dict[str, Any] = {
        "name": config.name,
        "description": config.description,
        "status": config.status,
        "steps": _steps_to_payload(config.steps),
        "input_schema": config.input_schema,
        "add_workflow_history_to_steps": config.add_workflow_history_to_steps,
        "stream_executor_events": config.stream_executor_events,
        "tags": list(config.tags),
        "metadata_": dict(config.metadata or {}),
        "user_id": config.user_id,
    }

    return data


def _steps_to_payload(steps: list[StepConfig]) -> list[dict[str, Any]]:
    return [step.model_dump(mode="json", exclude_none=True) for step in steps]
