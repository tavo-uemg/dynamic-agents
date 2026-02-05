"""Custom exception hierarchy for the dynamic agents core layer."""

from __future__ import annotations

__all__ = [
    "CoreError",
    "AgentFactoryError",
    "AgentNotFoundError",
    "AgentRepositoryError",
    "AgentSerializationError",
    "ToolRegistryError",
    "MCPConnectionError",
]


class CoreError(RuntimeError):
    """Base error for all core management components."""


class AgentFactoryError(CoreError):
    """Raised when an agent cannot be assembled or configured."""


class AgentNotFoundError(AgentFactoryError):
    """Raised when a requested agent configuration cannot be located."""


class AgentRepositoryError(CoreError):
    """Raised when persistence operations fail."""


class AgentSerializationError(CoreError):
    """Raised when converting between ORM models and schemas fails."""


class ToolRegistryError(CoreError):
    """Raised when a tool configuration cannot be resolved."""


class MCPConnectionError(ToolRegistryError):
    """Raised when a Model Context Protocol connection cannot be established."""
