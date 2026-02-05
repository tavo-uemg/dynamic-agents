"""Team CRUD API endpoints."""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from ...core.team_repository import TeamRepositoryError
from ...schemas import TeamCreate, TeamResponse, TeamUpdate
from ..deps import TeamRepo

router = APIRouter()


def _handle_repository_error(exc: TeamRepositoryError) -> None:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(exc),
    ) from exc


def _serialize_team(model: object) -> TeamResponse:
    return TeamResponse.model_validate(model)


@router.post("/", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(team: TeamCreate, repo: TeamRepo) -> TeamResponse:
    """Persist a new team configuration."""

    try:
        record = await repo.create(team)
    except TeamRepositoryError as exc:
        _handle_repository_error(exc)
    return _serialize_team(record)


@router.get("/", response_model=List[TeamResponse])
async def list_teams(
    repo: TeamRepo,
    skip: int = 0,
    limit: int = 100,
    tags: list[str] | None = Query(default=None),
) -> list[TeamResponse]:
    """Return a filtered list of stored teams."""

    try:
        records = await repo.list(tags=tags, limit=limit, offset=skip)
    except TeamRepositoryError as exc:
        _handle_repository_error(exc)
    return [_serialize_team(record) for record in records]


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(team_id: UUID, repo: TeamRepo) -> TeamResponse:
    """Return a single team by identifier."""

    try:
        record = await repo.get(team_id)
    except TeamRepositoryError as exc:
        _handle_repository_error(exc)
        raise
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return _serialize_team(record)


@router.patch("/{team_id}", response_model=TeamResponse)
async def update_team(team_id: UUID, team: TeamUpdate, repo: TeamRepo) -> TeamResponse:
    """Apply partial updates to an existing team."""

    try:
        record = await repo.update(team_id, team)
    except TeamRepositoryError as exc:
        _handle_repository_error(exc)
        raise
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return _serialize_team(record)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(team_id: UUID, repo: TeamRepo) -> None:
    """Delete a team by identifier."""

    try:
        deleted = await repo.delete(team_id)
    except TeamRepositoryError as exc:
        _handle_repository_error(exc)
        return
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")


__all__ = ["router"]
