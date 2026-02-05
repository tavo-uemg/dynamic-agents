"""Team ORM model and supporting enums."""

from __future__ import annotations

from enum import Enum
from typing import Any, TYPE_CHECKING

from sqlalchemy import Boolean, Enum as SqlEnum, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, JSONBType, TimestampMixin, UUIDPrimaryKey, UserOwnedMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .executions import ExecutionRecord


class TeamStatus(str, Enum):
    """Possible lifecycle states for a team configuration."""

    DRAFT = "draft"
    ACTIVE = "active"
    DISABLED = "disabled"


class TeamModel(UUIDPrimaryKey, TimestampMixin, UserOwnedMixin, Base):
    """Persistence model for agent teams and coordination settings."""

    __tablename__ = "teams"
    __table_args__ = (
        Index("ix_teams_name", "name"),
        Index("ix_teams_user_id", "user_id"),
        Index("ix_teams_tags", "tags"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    status: Mapped[TeamStatus] = mapped_column(
        SqlEnum(TeamStatus, name="team_status"),
        default=TeamStatus.DRAFT,
        nullable=False,
    )

    model_config: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    member_ids: Mapped[list[str]] = mapped_column(JSONBType, default=list, nullable=False)
    instructions: Mapped[list[str]] = mapped_column(JSONBType, default=list, nullable=False)

    respond_directly: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delegate_to_all_members: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    share_member_interactions: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    add_team_history_to_members: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    num_team_history_runs: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    get_member_information_tool: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    store_member_responses: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    tags: Mapped[list[str]] = mapped_column(JSONBType, default=list, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONBType,
        default=dict,
        nullable=False,
    )

    executions: Mapped[list["ExecutionRecord"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


__all__ = ["TeamModel", "TeamStatus"]
