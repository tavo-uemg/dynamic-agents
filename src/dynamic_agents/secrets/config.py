"""Configuration for the A8N Identity secrets integration."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Callable, TypeAlias, cast


class _BaseSettingsProtocol:
    model_config: dict[str, Any]


FieldCallable: TypeAlias = Callable[..., Any]
SettingsConfigDict: TypeAlias = dict[str, Any]


try:
    Field = cast(FieldCallable, getattr(import_module("pydantic"), "Field"))
except ModuleNotFoundError as exc:  # pragma: no cover - defensive
    raise RuntimeError("pydantic must be installed to use SecretsConfig") from exc

try:
    _settings_module = import_module("pydantic_settings")
except ModuleNotFoundError as exc:  # pragma: no cover - defensive
    raise RuntimeError("pydantic-settings must be installed to use SecretsConfig") from exc

BaseSettings = cast(type[_BaseSettingsProtocol], getattr(_settings_module, "BaseSettings"))


class SecretsConfig(BaseSettings):
    """Settings used by :class:`dynamic_agents.secrets.manager.SecretsManager`."""

    identity_url: str = Field(
        default="http://localhost:8000",
        description="Base URL of the A8N Identity API",
    )
    service_token: str = Field(
        ..., description="Service access token used for Bearer authentication"
    )
    cache_ttl: int = Field(
        default=300,
        ge=1,
        description="Cache TTL (seconds) applied to decrypted secrets",
    )
    cache_max_size: int = Field(
        default=100,
        ge=1,
        description="Maximum number of cached provider payloads",
    )
    timeout: float = Field(
        default=10.0,
        gt=0,
        description="HTTP timeout (seconds) for Identity API requests",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Number of retries for transient HTTP errors",
    )
    retry_backoff_seconds: float = Field(
        default=0.5,
        gt=0,
        description="Base delay (seconds) for exponential backoff between retries",
    )
    verify_ssl: bool = Field(
        default=True,
        description="Whether to verify TLS certificates when calling Identity",
    )

    model_config: SettingsConfigDict = {
        "env_prefix": "A8N_",
        "env_file": ".env",
        "extra": "ignore",
    }


__all__ = ["SecretsConfig"]
