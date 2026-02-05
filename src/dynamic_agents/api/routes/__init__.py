"""Router exports for the API module."""

from .agents import router as agents_router
from .execute import router as execute_router
from .health import router as health_router
from .router import router as router_router
from .teams import router as teams_router

__all__ = [
    "agents_router",
    "execute_router",
    "health_router",
    "router_router",
    "teams_router",
]
