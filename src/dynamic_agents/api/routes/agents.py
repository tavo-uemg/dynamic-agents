"""Agent CRUD API endpoints."""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from ...core.exceptions import AgentRepositoryError
from ...schemas import AgentCreate, AgentResponse, AgentUpdate
from ..deps import AgentRepo

router = APIRouter()


def _handle_repository_error(exc: AgentRepositoryError) -> None:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(exc),
    ) from exc


def _serialize_agent(model: object) -> AgentResponse:
    return AgentResponse.model_validate(model)


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(agent: AgentCreate, repo: AgentRepo) -> AgentResponse:
    """Persist a new agent configuration."""

    try:
        record = await repo.create(agent)
    except AgentRepositoryError as exc:
        _handle_repository_error(exc)
    return _serialize_agent(record)


@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    repo: AgentRepo,
    skip: int = 0,
    limit: int = 100,
    tags: list[str] | None = Query(default=None),
) -> list[AgentResponse]:
    """Return a filtered list of stored agents."""

    try:
        records = await repo.list(tags=tags, limit=limit, offset=skip)
    except AgentRepositoryError as exc:
        _handle_repository_error(exc)
    return [_serialize_agent(record) for record in records]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: UUID, repo: AgentRepo) -> AgentResponse:
    """Return a single agent by identifier."""

    try:
        record = await repo.get(agent_id)
    except AgentRepositoryError as exc:
        _handle_repository_error(exc)
        raise  # Satisfy type checker; unreachable.
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return _serialize_agent(record)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: UUID, agent: AgentUpdate, repo: AgentRepo) -> AgentResponse:
    """Apply partial updates to an existing agent."""

    try:
        record = await repo.update(agent_id, agent)
    except AgentRepositoryError as exc:
        _handle_repository_error(exc)
        raise
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return _serialize_agent(record)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: UUID, repo: AgentRepo) -> None:
    """Delete the agent with the provided identifier."""

    try:
        deleted = await repo.delete(agent_id)
    except AgentRepositoryError as exc:
        _handle_repository_error(exc)
        return
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")


__all__ = ["router"]
