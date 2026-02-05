"""Workflow CRUD API endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from ...core.workflow_repository import WorkflowRepositoryError
from ...models import WorkflowStatus
from ...schemas import WorkflowCreate, WorkflowResponse, WorkflowUpdate
from ..deps import WorkflowRepo

router = APIRouter()


def _handle_repository_error(exc: WorkflowRepositoryError) -> None:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(exc),
    ) from exc


def _serialize_workflow(model: object) -> WorkflowResponse:
    return WorkflowResponse.model_validate(model)


@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(workflow: WorkflowCreate, repo: WorkflowRepo) -> WorkflowResponse:
    """Persist a new workflow configuration."""

    try:
        record = await repo.create(workflow)
    except WorkflowRepositoryError as exc:
        _handle_repository_error(exc)
        raise
    return _serialize_workflow(record)


@router.get("/", response_model=list[WorkflowResponse])
async def list_workflows(
    repo: WorkflowRepo,
    skip: int = 0,
    limit: int = 100,
    tags: list[str] | None = Query(default=None),
    status_filter: WorkflowStatus | None = Query(default=None, alias="status"),
) -> list[WorkflowResponse]:
    """Return a filtered list of stored workflows."""

    try:
        records = await repo.list(tags=tags, status=status_filter, limit=limit, offset=skip)
    except WorkflowRepositoryError as exc:
        _handle_repository_error(exc)
        raise
    return [_serialize_workflow(record) for record in records]


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: UUID, repo: WorkflowRepo) -> WorkflowResponse:
    """Return a single workflow by identifier."""

    try:
        record = await repo.get(workflow_id)
    except WorkflowRepositoryError as exc:
        _handle_repository_error(exc)
        raise
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return _serialize_workflow(record)


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    workflow: WorkflowUpdate,
    repo: WorkflowRepo,
) -> WorkflowResponse:
    """Apply partial updates to an existing workflow."""

    try:
        record = await repo.update(workflow_id, workflow)
    except WorkflowRepositoryError as exc:
        _handle_repository_error(exc)
        raise
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return _serialize_workflow(record)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(workflow_id: UUID, repo: WorkflowRepo) -> None:
    """Delete the workflow with the provided identifier."""

    try:
        deleted = await repo.delete(workflow_id)
    except WorkflowRepositoryError as exc:
        _handle_repository_error(exc)
        return
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")


__all__ = ["router"]
