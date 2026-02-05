"""Team schema definitions."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field

from ..models import TeamStatus
from .base import IdentifiedSchema, ORMModel
from .router import ModelConfig


class TeamConfigBase(ORMModel):
    """Shared schema for team configuration payloads."""

    name: str
    description: str | None = None
    status: TeamStatus = TeamStatus.DRAFT
    model_config: ModelConfig
    member_ids: list[str] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)

    respond_directly: bool = False
    delegate_to_all_members: bool = False
    share_member_interactions: bool = False
    add_team_history_to_members: bool = False
    num_team_history_runs: int = 3
    get_member_information_tool: bool = False
    store_member_responses: bool = False

    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TeamConfig(TeamConfigBase):
    """Stored team configuration representation."""

    user_id: UUID | None = None


class TeamCreate(TeamConfigBase):
    """Payload used when creating teams."""

    user_id: UUID | None = None


class TeamUpdate(ORMModel):
    """Partial update payload for teams."""

    name: str | None = None
    description: str | None = None
    status: TeamStatus | None = None
    model_config: ModelConfig | None = None
    member_ids: list[str] | None = None
    instructions: list[str] | None = None
    respond_directly: bool | None = None
    delegate_to_all_members: bool | None = None
    share_member_interactions: bool | None = None
    add_team_history_to_members: bool | None = None
    num_team_history_runs: int | None = None
    get_member_information_tool: bool | None = None
    store_member_responses: bool | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class TeamResponse(IdentifiedSchema, TeamConfigBase):
    """Response payload for persisted teams."""

    user_id: UUID | None = None


__all__ = ["TeamConfig", "TeamCreate", "TeamResponse", "TeamUpdate"]
