"""Pydantic settings for configuring the LiteLLM router."""

from __future__ import annotations

from typing import Any, ClassVar


def _import_attr(module_name: str, attr_name: str) -> Any:
    import importlib

    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:  # pragma: no cover - dependency validation
        raise ImportError(
            f"Module '{module_name}' is required to configure the LiteLLM router"
        ) from exc
    try:
        return getattr(module, attr_name)
    except AttributeError as exc:  # pragma: no cover - dependency validation
        raise ImportError(
            f"Attribute '{attr_name}' was not found in '{module_name}'. Upgrade your dependencies."
        ) from exc


BaseSettings = _import_attr("pydantic_settings", "BaseSettings")
ConfigDict = _import_attr("pydantic", "ConfigDict")
Field = _import_attr("pydantic", "Field")

from .schemas import ModelDeployment


class RouterConfig(BaseSettings):
    """Runtime configuration for the LiteLLM router."""

    model_list: list[ModelDeployment] = Field(default_factory=list)
    routing_strategy: str = "usage-based-routing-v2"
    num_retries: int = 3
    fallbacks: dict[str, list[str]] = Field(default_factory=dict)
    default_fallbacks: list[str] = Field(default_factory=list)
    context_window_fallbacks: dict[str, list[str]] = Field(default_factory=dict)
    allowed_fails: int = 3
    cooldown_time: float = 30.0
    enable_pre_call_checks: bool = True
    enable_tag_filtering: bool = True

    redis_host: str | None = None
    redis_port: int = 6379
    redis_password: str | None = None
    redis_url: str | None = None

    model_config: ClassVar[dict[str, str]] = ConfigDict(  # pyright: ignore[reportIncompatibleVariableOverride]
        env_prefix="LITELLM_",
        env_nested_delimiter="__",
    )


__all__ = ["RouterConfig"]
