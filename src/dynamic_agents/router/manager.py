"""LiteLLM router manager with hot-reload and persistence support."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Protocol, Sequence

from litellm import Router
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models import ModelDeploymentModel, RouterConfigModel, RouterStatus, RoutingStrategy
from ..secrets import ENV_REFERENCE_PREFIX, SecretsManager
from ..storage.database import get_session_factory
from .config import RouterConfig
from .schemas import ModelDeployment, RouterHealthInfo


class RouterConfigRepository(Protocol):
    """Repository contract for persisting router configuration snapshots."""

    async def load_config(self) -> RouterConfig | None:  # pragma: no cover - protocol
        """Retrieve the most recent RouterConfig, if any."""

    async def save_config(self, config: RouterConfig) -> None:  # pragma: no cover - protocol
        """Persist the RouterConfig instance."""

    async def list_deployments(self) -> list[ModelDeployment]:  # pragma: no cover - protocol
        """Return all persisted deployments."""


class InMemoryRouterConfigRepository:
    """Fallback repository used when a database connection is unavailable."""

    def __init__(self) -> None:
        self._config: RouterConfig | None = None

    async def load_config(self) -> RouterConfig | None:
        return self._config

    async def save_config(self, config: RouterConfig) -> None:
        self._config = config

    async def list_deployments(self) -> list[ModelDeployment]:
        if not self._config:
            return []
        return [
            ModelDeployment.model_validate(deployment.model_dump())
            for deployment in self._config.model_list
        ]


class SQLRouterConfigRepository:
    """Persist router configuration using the SQLAlchemy models."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        *,
        router_name: str = "default-router",
    ) -> None:
        self._session_factory = session_factory or get_session_factory()
        self._router_name = router_name

    async def load_config(self) -> RouterConfig | None:
        async with self._session_factory() as session:
            stmt = select(RouterConfigModel).where(RouterConfigModel.name == self._router_name)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            deployments = await self._fetch_deployments(session, model.id)
            return RouterConfig(
                model_list=deployments,
                routing_strategy=model.routing_strategy.value,
                num_retries=model.num_retries,
                fallbacks=model.fallbacks,
                default_fallbacks=model.default_fallbacks,
                context_window_fallbacks=model.context_window_fallbacks,
                allowed_fails=model.allowed_fails,
                cooldown_time=model.cooldown_time,
                enable_pre_call_checks=model.enable_pre_call_checks,
                enable_tag_filtering=model.enable_tag_filtering,
                redis_host=model.redis_host,
                redis_port=model.redis_port or 6379,
                redis_password=model.redis_password,
                redis_url=None,
            )

    async def save_config(self, config: RouterConfig) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                model = await self._get_or_create(session)
                self._apply_config(model, config)
                await session.flush()
                await session.execute(
                    delete(ModelDeploymentModel).where(
                        ModelDeploymentModel.router_config_id == model.id
                    )
                )
                for deployment in config.model_list:
                    session.add(
                        ModelDeploymentModel(
                            router_config_id=model.id,
                            model_name=deployment.model_name,
                            litellm_params=deployment.litellm_params,
                            model_info=deployment.model_info,
                            tags=self._extract_tags(deployment),
                        )
                    )

    async def list_deployments(self) -> list[ModelDeployment]:
        async with self._session_factory() as session:
            stmt = select(RouterConfigModel).where(RouterConfigModel.name == self._router_name)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return []
            return await self._fetch_deployments(session, model.id)

    async def _fetch_deployments(
        self, session: AsyncSession, config_id: Any
    ) -> list[ModelDeployment]:
        stmt = select(ModelDeploymentModel).where(
            ModelDeploymentModel.router_config_id == config_id
        )
        result = await session.execute(stmt)
        records = result.scalars().all()
        return [
            ModelDeployment(
                model_name=record.model_name,
                litellm_params=record.litellm_params,
                model_info=record.model_info,
            )
            for record in records
        ]

    async def _get_or_create(self, session: AsyncSession) -> RouterConfigModel:
        stmt = select(RouterConfigModel).where(RouterConfigModel.name == self._router_name)
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is not None:
            return model
        model = RouterConfigModel(
            name=self._router_name,
            status=RouterStatus.ACTIVE,
            routing_strategy=RoutingStrategy.SIMPLE_SHUFFLE,
            num_retries=3,
            timeout=60.0,
            allowed_fails=3,
            cooldown_time=30.0,
        )
        session.add(model)
        await session.flush()
        return model

    def _apply_config(self, model: RouterConfigModel, config: RouterConfig) -> None:
        model.routing_strategy = self._map_strategy(config.routing_strategy)
        model.num_retries = config.num_retries
        model.allowed_fails = config.allowed_fails
        model.cooldown_time = config.cooldown_time
        model.fallbacks = config.fallbacks
        model.default_fallbacks = config.default_fallbacks
        model.context_window_fallbacks = config.context_window_fallbacks
        model.enable_pre_call_checks = config.enable_pre_call_checks
        model.enable_tag_filtering = config.enable_tag_filtering
        model.redis_host = config.redis_host
        model.redis_port = config.redis_port
        model.redis_password = config.redis_password

        metadata = dict(model.metadata_) if isinstance(model.metadata_, dict) else {}
        metadata["router_settings"] = config.model_dump(mode="json")
        model.metadata_ = metadata

    def _map_strategy(self, value: str) -> RoutingStrategy:
        normalized = value.lower().strip()
        mapping = {
            "simple-shuffle": RoutingStrategy.SIMPLE_SHUFFLE,
            "least-busy": RoutingStrategy.LEAST_BUSY,
            "latency-based-routing": RoutingStrategy.LATENCY_BASED,
            "usage-based-routing": RoutingStrategy.USAGE_BASED,
            "usage-based-routing-v2": RoutingStrategy.USAGE_BASED,
            "cost-based-routing": RoutingStrategy.COST_BASED,
        }
        return mapping.get(normalized, RoutingStrategy.SIMPLE_SHUFFLE)

    def _extract_tags(self, deployment: ModelDeployment) -> list[str]:
        tags = deployment.litellm_params.get("tags")
        if isinstance(tags, list):
            return [tag for tag in tags if isinstance(tag, str)]
        return []


class RouterManager:
    """Manager that orchestrates LiteLLM Router instances and configuration."""

    def __init__(
        self,
        config: RouterConfig,
        secrets_manager: SecretsManager | None = None,
        repository: RouterConfigRepository | None = None,
    ) -> None:
        self._logger = logging.getLogger(__name__)
        self._config = config
        self._secrets_manager = secrets_manager
        self._lock = asyncio.Lock()
        self._router: Router | None = None
        self._last_reload_at: datetime | None = None
        self._repository = repository or self._build_default_repository()

    async def initialize(self) -> None:
        """Create the LiteLLM Router instance if it does not exist."""

        async with self._lock:
            if self._router is not None:
                return
            persisted = await self._repository.load_config()
            if persisted is not None:
                self._config = persisted
            self._router = await self._build_router(self._config)
            await self._repository.save_config(self._config)

    async def reload_config(self, new_config: RouterConfig) -> None:
        """Hot reload the router with a brand new configuration."""

        await self._apply_new_config(new_config)

    async def add_deployment(self, deployment: ModelDeployment) -> None:
        """Append a deployment and hot-reload the router."""

        new_list = list(self._config.model_list)
        new_list.append(deployment)
        await self.reload_config(self._config.model_copy(update={"model_list": new_list}))

    async def remove_deployment(self, model_name: str, deployment_id: str) -> None:
        """Remove a deployment by identifier and hot-reload."""

        remaining: list[ModelDeployment] = []
        removed = False
        for deployment in self._config.model_list:
            if deployment.model_name != model_name:
                remaining.append(deployment)
                continue
            if self._matches_deployment_id(deployment, deployment_id):
                removed = True
                continue
            remaining.append(deployment)
        if not removed:
            raise ValueError(f"Deployment '{deployment_id}' for model '{model_name}' was not found")
        await self.reload_config(self._config.model_copy(update={"model_list": remaining}))

    async def list_deployments(self) -> list[ModelDeployment]:
        """Return the in-memory deployment list."""

        return [
            ModelDeployment.model_validate(deployment.model_dump())
            for deployment in self._config.model_list
        ]

    async def get_health_info(self) -> RouterHealthInfo:
        """Return a structured payload for health endpoints."""

        router = self._router
        return RouterHealthInfo(
            initialized=router is not None,
            routing_strategy=self._config.routing_strategy,
            total_deployments=len(self._config.model_list),
            last_reload_at=self._last_reload_at,
            redis_enabled=bool(self._config.redis_url or self._config.redis_host),
            redis_url=self._config.redis_url or self._build_redis_url(),
            allowed_fails=self._config.allowed_fails,
            cooldown_time=self._config.cooldown_time,
            num_retries=self._config.num_retries,
            tag_filtering_enabled=self._config.enable_tag_filtering,
        )

    async def completion(self, model: str, messages: list[Any], **kwargs: Any) -> Any:
        """Proxy to the router completion API (sync under the hood)."""

        router = await self._ensure_router()
        return await asyncio.to_thread(router.completion, model=model, messages=messages, **kwargs)

    async def acompletion(self, model: str, messages: list[Any], **kwargs: Any) -> Any:
        """Proxy to the async router completion API."""

        router = await self._ensure_router()
        return await router.acompletion(model=model, messages=messages, **kwargs)

    def get_router(self) -> Router:
        """Expose the underlying LiteLLM Router instance."""

        if self._router is None:
            raise RuntimeError("Router has not been initialized")
        return self._router

    async def _apply_new_config(self, new_config: RouterConfig) -> None:
        async with self._lock:
            resolved_models = await self._resolve_model_list(new_config.model_list)
            needs_rebuild = self._requires_full_rebuild(self._config, new_config)
            self._config = new_config
            await self._repository.save_config(new_config)
            if self._router is None or needs_rebuild:
                self._router = await self._build_router(new_config, resolved_models)
            else:
                await asyncio.to_thread(self._router.set_model_list, resolved_models)
                self._last_reload_at = datetime.now(timezone.utc)

    async def _ensure_router(self) -> Router:
        if self._router is None:
            await self.initialize()
        assert self._router is not None  # nosec - guarded above
        return self._router

    async def _build_router(
        self, config: RouterConfig, resolved_model_list: list[dict[str, Any]] | None = None
    ) -> Router:
        model_payload = resolved_model_list or await self._resolve_model_list(config.model_list)
        guardrails_payload = await self._resolve_guardrails(config.guardrails)
        kwargs = self._router_kwargs(config, model_payload, guardrails_payload)
        router = await asyncio.to_thread(Router, **kwargs)
        self._last_reload_at = datetime.now(timezone.utc)
        return router

    async def _resolve_model_list(
        self, deployments: Sequence[ModelDeployment]
    ) -> list[dict[str, Any]]:
        resolved: list[dict[str, Any]] = []
        for deployment in deployments:
            payload = deployment.model_dump()
            params = dict(payload["litellm_params"])
            for key, value in list(params.items()):
                if isinstance(value, str) and value.startswith(ENV_REFERENCE_PREFIX):
                    resolved_value = await self._resolve_secret_value(value)
                    if resolved_value is not None:
                        params[key] = resolved_value
            payload["litellm_params"] = params
            resolved.append(payload)
        return resolved

    async def _resolve_guardrails(self, guardrails: Sequence[Any]) -> list[dict[str, Any]]:
        resolved: list[dict[str, Any]] = []
        for gr in guardrails:
            payload = gr.model_dump()
            params = dict(payload["litellm_params"])
            for key, value in list(params.items()):
                if isinstance(value, str) and value.startswith(ENV_REFERENCE_PREFIX):
                    resolved_value = await self._resolve_secret_value(value)
                    if resolved_value is not None:
                        params[key] = resolved_value
            payload["litellm_params"] = params
            resolved.append(payload)
        return resolved

    async def _resolve_secret_value(self, reference: str) -> str | None:
        if not reference.startswith(ENV_REFERENCE_PREFIX):
            return reference
        if self._secrets_manager is not None:
            resolver = getattr(self._secrets_manager, "resolve_env_reference", None)
            if callable(resolver):
                resolved = await resolver(reference)
                if resolved:
                    return resolved
            resolved = await self._secrets_manager.resolve_reference(reference)
            if resolved:
                return resolved
        env_name = reference[len(ENV_REFERENCE_PREFIX) :].strip()
        return os.getenv(env_name)

    def _router_kwargs(
        self,
        config: RouterConfig,
        model_list: list[dict[str, Any]],
        guardrails: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model_list": model_list,
            "routing_strategy": config.routing_strategy,
            "num_retries": config.num_retries,
            "fallbacks": self._format_fallbacks(config),
            "context_window_fallbacks": self._format_context_window_fallbacks(config),
            "allowed_fails": config.allowed_fails,
            "cooldown_time": config.cooldown_time,
            "enable_pre_call_checks": config.enable_pre_call_checks,
            "enable_tag_filtering": config.enable_tag_filtering,
        }
        if guardrails:
            kwargs["guardrails"] = guardrails
        if config.redis_url:
            kwargs["redis_url"] = config.redis_url
        else:
            kwargs.update(
                {
                    "redis_host": config.redis_host,
                    "redis_port": config.redis_port,
                    "redis_password": config.redis_password,
                }
            )
        if config.default_fallbacks and not kwargs["fallbacks"]:
            kwargs["fallbacks"] = [{"*": config.default_fallbacks}]
        return kwargs

    def _format_fallbacks(self, config: RouterConfig) -> list[dict[str, list[str]]]:
        entries: list[dict[str, list[str]]] = []
        for model_name, targets in config.fallbacks.items():
            if targets:
                entries.append({model_name: targets})
        if config.default_fallbacks:
            existing = {next(iter(entry.keys())) for entry in entries}
            for deployment in config.model_list:
                if deployment.model_name not in existing:
                    entries.append({deployment.model_name: config.default_fallbacks})
        return entries

    def _format_context_window_fallbacks(self, config: RouterConfig) -> list[dict[str, list[str]]]:
        return [
            {model_name: targets}
            for model_name, targets in config.context_window_fallbacks.items()
            if targets
        ]

    def _requires_full_rebuild(self, current: RouterConfig, new_config: RouterConfig) -> bool:
        sensitive_fields = [
            "routing_strategy",
            "num_retries",
            "fallbacks",
            "default_fallbacks",
            "context_window_fallbacks",
            "allowed_fails",
            "cooldown_time",
            "enable_pre_call_checks",
            "enable_tag_filtering",
            "redis_host",
            "redis_port",
            "redis_password",
            "redis_url",
            "guardrails",
        ]
        return any(
            getattr(current, field) != getattr(new_config, field) for field in sensitive_fields
        )

    def _matches_deployment_id(self, deployment: ModelDeployment, deployment_id: str) -> bool:
        candidate_keys = ("deployment_id", "id")
        for key in candidate_keys:
            value = deployment.litellm_params.get(key)
            if isinstance(value, str) and value == deployment_id:
                return True
        model_info_id = (deployment.model_info or {}).get("id") if deployment.model_info else None
        return isinstance(model_info_id, str) and model_info_id == deployment_id

    def _build_redis_url(self) -> str | None:
        if not self._config.redis_host:
            return None
        password = self._config.redis_password
        auth = f":{password}@" if password else ""
        return f"redis://{auth}{self._config.redis_host}:{self._config.redis_port}"

    def _build_default_repository(self) -> RouterConfigRepository:
        try:
            return SQLRouterConfigRepository()
        except (RuntimeError, SQLAlchemyError):
            self._logger.warning(
                "Falling back to in-memory router repository; database unavailable"
            )
            return InMemoryRouterConfigRepository()


__all__ = [
    "InMemoryRouterConfigRepository",
    "RouterConfigRepository",
    "RouterManager",
    "SQLRouterConfigRepository",
]
