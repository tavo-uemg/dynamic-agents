"""LiteLLM router configuration ORM models."""

from __future__ import annotations

from enum import Enum
from typing import Any, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Enum as SqlEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, GUID, JSONBType, TimestampMixin, UUIDPrimaryKey, UserOwnedMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .executions import ExecutionRecord


class RoutingStrategy(str, Enum):
    """Supported LiteLLM routing strategies."""

    SIMPLE_SHUFFLE = "simple-shuffle"
    LEAST_BUSY = "least-busy"
    USAGE_BASED = "usage-based-routing"
    LATENCY_BASED = "latency-based-routing"
    COST_BASED = "cost-based-routing"


class RouterStatus(str, Enum):
    """Lifecycle status for router configurations."""

    ACTIVE = "active"
    DISABLED = "disabled"
    ARCHIVED = "archived"


class ModelDeploymentStatus(str, Enum):
    """Status of an individual deployment entry."""

    ACTIVE = "active"
    COOLDOWN = "cooldown"
    DISABLED = "disabled"


class RouterConfigModel(UUIDPrimaryKey, TimestampMixin, UserOwnedMixin, Base):
    """Represents a snapshot of router configuration and state."""

    __tablename__ = "router_configs"
    __table_args__ = (
        Index("ix_router_configs_name", "name"),
        Index("ix_router_configs_user_id", "user_id"),
        Index("ix_router_configs_tags", "tags"),
    )

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    status: Mapped[RouterStatus] = mapped_column(
        SqlEnum(RouterStatus, name="router_status"),
        default=RouterStatus.ACTIVE,
        nullable=False,
    )

    routing_strategy: Mapped[RoutingStrategy] = mapped_column(
        SqlEnum(RoutingStrategy, name="routing_strategy"),
        default=RoutingStrategy.SIMPLE_SHUFFLE,
        nullable=False,
    )
    num_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    timeout: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)
    allowed_fails: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    cooldown_time: Mapped[float] = mapped_column(Float, default=30.0, nullable=False)

    fallbacks: Mapped[dict[str, list[str]]] = mapped_column(JSONBType, default=dict, nullable=False)
    default_fallbacks: Mapped[list[str]] = mapped_column(JSONBType, default=list, nullable=False)
    context_window_fallbacks: Mapped[dict[str, list[str]]] = mapped_column(
        JSONBType,
        default=dict,
        nullable=False,
    )
    content_policy_fallbacks: Mapped[dict[str, list[str]]] = mapped_column(
        JSONBType,
        default=dict,
        nullable=False,
    )

    enable_pre_call_checks: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_tag_filtering: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cache_responses: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_rate_limits: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    redis_host: Mapped[str | None] = mapped_column(String(255))
    redis_port: Mapped[int | None] = mapped_column(Integer)
    redis_password: Mapped[str | None] = mapped_column(String(255))

    tags: Mapped[list[str]] = mapped_column(JSONBType, default=list, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONBType,
        default=dict,
        nullable=False,
    )

    deployments: Mapped[list["ModelDeploymentModel"]] = relationship(
        back_populates="router_config",
        cascade="all, delete-orphan",
    )
    executions: Mapped[list["ExecutionRecord"]] = relationship(
        back_populates="router_config",
        cascade="all, delete-orphan",
    )


class ModelDeploymentModel(UUIDPrimaryKey, TimestampMixin, Base):
    """Individual LiteLLM deployment entry for routing."""

    __tablename__ = "model_deployments"
    __table_args__ = (
        Index("ix_model_deployments_router", "router_config_id"),
        Index("ix_model_deployments_model", "model_name"),
    )

    router_config_id: Mapped[UUID] = mapped_column(
        GUID(),
        ForeignKey("router_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ModelDeploymentStatus] = mapped_column(
        SqlEnum(ModelDeploymentStatus, name="model_deployment_status"),
        default=ModelDeploymentStatus.ACTIVE,
        nullable=False,
    )
    litellm_params: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    model_info: Mapped[dict[str, Any] | None] = mapped_column(JSONBType)
    weight: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONBType, default=list, nullable=False)

    router_config: Mapped[RouterConfigModel] = relationship(back_populates="deployments")


__all__ = [
    "ModelDeploymentModel",
    "ModelDeploymentStatus",
    "RouterConfigModel",
    "RouterStatus",
    "RoutingStrategy",
]
