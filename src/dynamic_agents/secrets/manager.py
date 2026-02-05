"""SecretsManager implementation backed by the A8N Identity API."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Mapping
from typing import Final

import httpx  # type: ignore[import]

from .cache import CacheManager
from .config import SecretsConfig
from .exceptions import (
    SecretNotFoundError,
    SecretsAPIError,
    SecretsAuthError,
    SecretsConfigError,
    SecretsManagerError,
    SecretsUnavailableError,
)
from .mappings import SecretScope, get_env_secret_mapping
from .schemas import SecretListResponse, SecretMetadata, SecretWithValues

ENV_REFERENCE_PREFIX: Final[str] = "os.environ/"


class SecretsManager:
    """Fetches and caches secrets stored in A8N Identity."""

    def __init__(
        self,
        config: SecretsConfig | None = None,
        cache: CacheManager[dict[str, str]] | None = None,
    ) -> None:
        self.config: SecretsConfig = config or SecretsConfig()
        cache_instance = cache or CacheManager(
            maxsize=self.config.cache_max_size,
            ttl_seconds=self.config.cache_ttl,
        )
        self._cache: CacheManager[dict[str, str]] = cache_instance
        self._client: httpx.AsyncClient | None = None
        self._client_lock: asyncio.Lock = asyncio.Lock()
        self._logger: logging.Logger = logging.getLogger(__name__)

    async def close(self) -> None:
        """Close the underlying HTTP client."""

        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def clear_cache(self) -> None:
        """Flush the local TTL cache."""

        await self._cache.clear()

    async def get_secret(
        self,
        provider: str,
        field: str,
        *,
        user_id: str | None = None,
        user_token: str | None = None,
        force_refresh: bool = False,
        raise_on_missing: bool = False,
    ) -> str | None:
        """Return the decrypted secret value for ``provider``/``field``."""

        scope = SecretScope.USER if user_id else SecretScope.SYSTEM
        cache_key = self._build_cache_key(provider, scope, user_id)

        if not force_refresh:
            payload = await self._cache.get(cache_key)
            if payload is not None:
                cached_value = payload.get(field)
                if cached_value is not None:
                    self._logger.debug(
                        "Cache hit for secret",
                        extra=self._log_context(provider, field, scope, user_id),
                    )
                    return cached_value

        token = self._resolve_token(scope=scope, user_token=user_token)

        try:
            payload = await self._fetch_provider_payload(
                provider=provider,
                token=token,
            )
        except SecretNotFoundError:
            self._logger.warning(
                "Secret metadata not found",
                extra=self._log_context(provider, field, scope, user_id),
            )
            if raise_on_missing:
                raise
            return None

        await self._cache.set(cache_key, dict(payload))
        value = payload.get(field)
        if value is not None:
            self._logger.debug(
                "Secret fetched from Identity API",
                extra=self._log_context(provider, field, scope, user_id),
            )
            return value

        self._logger.warning(
            "Field missing in secret payload",
            extra=self._log_context(provider, field, scope, user_id),
        )
        if raise_on_missing:
            raise SecretNotFoundError(f"Field '{field}' was not returned for provider '{provider}'")
        return None

    async def resolve_reference(
        self,
        reference: str | None,
        *,
        user_id: str | None = None,
        user_token: str | None = None,
        default: str | None = None,
    ) -> str | None:
        """Resolve ``os.environ/VAR`` references used by LiteLLM configurations."""

        if not reference:
            return None
        if not reference.startswith(ENV_REFERENCE_PREFIX):
            return reference

        env_name = reference[len(ENV_REFERENCE_PREFIX) :].strip()
        mapping = get_env_secret_mapping(env_name)
        if not mapping:
            return os.getenv(env_name, default)

        scope_user_id = user_id if mapping.scope is SecretScope.USER else None
        scope_user_token = user_token if mapping.scope is SecretScope.USER else None
        value = await self.get_secret(
            mapping.provider,
            mapping.field,
            user_id=scope_user_id,
            user_token=scope_user_token,
        )

        if value is not None:
            return value

        self._logger.debug(
            "Falling back to process environment for secret reference",
            extra={"env_name": env_name},
        )
        return os.getenv(env_name, default)

    async def _fetch_provider_payload(self, provider: str, *, token: str) -> dict[str, str]:
        metadata = await self._list_secrets(provider=provider, token=token)
        if not metadata:
            raise SecretNotFoundError(f"No secrets registered for provider '{provider}'")

        aggregated: dict[str, str] = {}
        for secret in metadata:
            secret_id = secret.id
            if not secret_id:
                continue
            values = await self._get_secret_values(secret_id=secret_id, token=token)
            for key, value in values.items():
                if isinstance(value, str):
                    aggregated[key] = value

        if not aggregated:
            raise SecretNotFoundError(f"Identity returned no values for provider '{provider}'")
        return aggregated

    async def _list_secrets(self, *, provider: str, token: str) -> list[SecretMetadata]:
        params: dict[str, str] = {"provider": provider}
        response = await self._request_with_retry(
            method="GET",
            url="/api/v1/secrets",
            token=token,
            params=params,
        )
        payload = await self._json(response, "Failed to decode secrets list response")

        if isinstance(payload, list):
            return [SecretMetadata.model_validate(item) for item in payload]

        wrapper = SecretListResponse.model_validate(payload)
        return wrapper.as_list()

    async def _get_secret_values(self, *, secret_id: str, token: str) -> Mapping[str, str]:
        response = await self._request_with_retry(
            method="GET",
            url=f"/api/v1/secrets/{secret_id}/values",
            token=token,
        )
        payload = await self._json(response, "Failed to decode secret values response")
        values = SecretWithValues.model_validate(payload)
        return values.values

    async def _request_with_retry(
        self,
        *,
        method: str,
        url: str,
        token: str,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        max_attempts = max(1, self.config.max_retries + 1)
        attempt = 0

        while attempt < max_attempts:
            attempt += 1
            try:
                client = await self._get_client()
                response = await client.request(
                    method,
                    url,
                    params=params,
                    headers=self._headers_for_token(token),
                )
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == httpx.codes.UNAUTHORIZED:
                    raise SecretsAuthError("Authentication failed with A8N Identity") from exc
                if status == httpx.codes.NOT_FOUND:
                    raise SecretNotFoundError("Requested secret resource was not found") from exc
                if status in {httpx.codes.TOO_MANY_REQUESTS} or 500 <= status < 600:
                    if attempt < max_attempts:
                        await asyncio.sleep(self._retry_delay(attempt))
                        continue
                raise SecretsAPIError(
                    f"Identity API returned {status}: {exc.response.text}"
                ) from exc
            except httpx.RequestError as exc:
                if attempt < max_attempts:
                    await asyncio.sleep(self._retry_delay(attempt))
                    continue
                raise SecretsUnavailableError("Unable to reach the A8N Identity API") from exc

        raise SecretsUnavailableError("Exceeded retry limit when contacting the Identity API")

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            async with self._client_lock:
                if self._client is None:
                    self._client = httpx.AsyncClient(
                        base_url=self.config.identity_url,
                        timeout=self.config.timeout,
                        verify=self.config.verify_ssl,
                        headers={"Accept": "application/json"},
                    )
        return self._client

    async def _json(self, response: httpx.Response, error: str) -> object:
        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise SecretsAPIError(error) from exc

    def _headers_for_token(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    def _retry_delay(self, attempt: int) -> float:
        return self.config.retry_backoff_seconds * (2 ** (attempt - 1))

    def _resolve_token(self, *, scope: SecretScope, user_token: str | None) -> str:
        if scope is SecretScope.USER:
            if not user_token:
                raise SecretsManagerError(
                    "user_token is required when requesting user-scoped secrets"
                )
            return user_token

        if not self.config.service_token:
            raise SecretsConfigError("Service token is required for system-scoped secrets")
        return self.config.service_token

    def _build_cache_key(self, provider: str, scope: SecretScope, user_id: str | None) -> str:
        owner = user_id or "system"
        return f"{scope.value}:{owner}:{provider.lower()}"

    def _log_context(
        self, provider: str, field: str, scope: SecretScope, user_id: str | None
    ) -> dict[str, dict[str, str | None]]:
        return {
            "secret_context": {
                "provider": provider,
                "field": field,
                "scope": scope.value,
                "user_id": user_id,
            }
        }


__all__ = [
    "ENV_REFERENCE_PREFIX",
    "SecretsManager",
]
