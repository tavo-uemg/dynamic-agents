"""FastAPI application factory for the Dynamic Agents API."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from ..storage.database import init_db
from .deps import get_router_manager, get_secrets_manager
from .routes import (
    agents_router,
    execute_router,
    health_router,
    router_router,
    teams_router,
    workflows_router,
)


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # noqa: ARG001 - signature requirement
        router_manager = get_router_manager()
        secrets_manager = get_secrets_manager()
        await init_db()
        await router_manager.initialize()
        try:
            yield
        finally:
            if secrets_manager is not None:
                await secrets_manager.close()

    app = FastAPI(
        title="Dynamic Agents API",
        description="REST API for managing AI agents, teams, and workflows",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(agents_router, prefix="/api/v1/agents", tags=["agents"])
    app.include_router(teams_router, prefix="/api/v1/teams", tags=["teams"])
    app.include_router(workflows_router, prefix="/api/v1/workflows", tags=["workflows"])
    app.include_router(execute_router, prefix="/api/v1/execute", tags=["execute"])
    app.include_router(router_router, prefix="/api/v1/router", tags=["router"])
    app.include_router(health_router, tags=["health"])

    return app


__all__ = ["create_app"]
