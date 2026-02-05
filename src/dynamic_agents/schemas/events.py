"""Event payload schemas used for Redis Streams and brokers."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from ..models import ExecutionStatus
from .base import ORMModel


class AgentRequestEvent(ORMModel):
    """Schema emitted when a client requests an agent execution."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_id: UUID
    session_id: str | None = None
    user_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentResponseEvent(ORMModel):
    """Schema published when execution outputs are returned."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    execution_id: UUID
    status: ExecutionStatus
    output: dict[str, Any] | None = None
    error: str | None = None
    tokens: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


__all__ = ["AgentRequestEvent", "AgentResponseEvent"]
