"""LiteLLM router configuration endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, status

from ...router.config import RouterConfig as RouterSettings
from ...router.schemas import ModelDeployment, RouterHealthInfo
from ..deps import RouterManagerDep

router = APIRouter()


def _current_config(manager: RouterManagerDep) -> RouterSettings:
    config = getattr(manager, "_config", None)
    if config is None:
        raise RuntimeError("Router manager configuration is unavailable")
    return config


@router.get("/config", response_model=RouterSettings)
async def get_router_config(manager: RouterManagerDep) -> RouterSettings:
    """Return the currently active router configuration."""

    return RouterSettings.model_validate(_current_config(manager))


@router.put("/config", response_model=RouterSettings)
async def update_router_config(
    payload: RouterSettings,
    manager: RouterManagerDep,
) -> RouterSettings:
    """Replace the active router configuration."""

    await manager.reload_config(payload)
    return RouterSettings.model_validate(payload)


@router.get("/deployments", response_model=List[ModelDeployment])
async def list_deployments(manager: RouterManagerDep) -> list[ModelDeployment]:
    """List all LiteLLM deployments currently configured."""

    return await manager.list_deployments()


@router.post(
    "/deployments",
    response_model=ModelDeployment,
    status_code=status.HTTP_201_CREATED,
)
async def add_deployment(
    deployment: ModelDeployment,
    manager: RouterManagerDep,
) -> ModelDeployment:
    """Append a deployment to the router configuration."""

    await manager.add_deployment(deployment)
    return deployment


@router.delete("/deployments/{model_name}/{deployment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_deployment(model_name: str, deployment_id: str, manager: RouterManagerDep) -> None:
    """Remove a deployment identified by model and deployment identifiers."""

    try:
        await manager.remove_deployment(model_name, deployment_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/health", response_model=RouterHealthInfo)
async def router_health(manager: RouterManagerDep) -> RouterHealthInfo:
    """Return router-specific health metadata."""

    return await manager.get_health_info()


__all__ = ["router"]
