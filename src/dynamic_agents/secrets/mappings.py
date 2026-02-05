"""Environment variable → provider mappings used by the SecretsManager."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Dict


class SecretScope(StrEnum):
    """Supported scopes for secrets retrieved from Identity."""

    SYSTEM = "system"
    USER = "user"


@dataclass(frozen=True, slots=True)
class EnvSecretMapping:
    """Describes how an env var maps to an Identity provider/field."""

    provider: str
    field: str
    scope: SecretScope = SecretScope.SYSTEM


ENV_SECRET_MAPPINGS: Dict[str, EnvSecretMapping] = {
    "OPENAI_API_KEY": EnvSecretMapping("openai", "api_key"),
    "OPENAI_ORG_ID": EnvSecretMapping("openai", "org_id"),
    "ANTHROPIC_API_KEY": EnvSecretMapping("anthropic", "api_key"),
    "GROQ_API_KEY": EnvSecretMapping("groq", "api_key"),
    "AZURE_OPENAI_API_KEY": EnvSecretMapping("azure_openai", "api_key"),
    "AZURE_OPENAI_ENDPOINT": EnvSecretMapping("azure_openai", "endpoint"),
    "AZURE_OPENAI_API_VERSION": EnvSecretMapping("azure_openai", "api_version"),
    "DISCORD_BOT_TOKEN": EnvSecretMapping("discord", "bot_token"),
    "DISCORD_APPLICATION_ID": EnvSecretMapping("discord", "application_id"),
    "SLACK_BOT_TOKEN": EnvSecretMapping("slack", "bot_token"),
    "SLACK_APP_TOKEN": EnvSecretMapping("slack", "app_token"),
    "GOOGLE_API_KEY": EnvSecretMapping("google", "api_key"),
    # Example user-scoped mapping for per-user deployments
    "USER_OPENAI_API_KEY": EnvSecretMapping("openai", "api_key", scope=SecretScope.USER),
}


def get_env_secret_mapping(env_name: str) -> EnvSecretMapping | None:
    """Return the mapping entry for ``env_name`` if it exists."""

    return ENV_SECRET_MAPPINGS.get(env_name.upper())


__all__ = [
    "EnvSecretMapping",
    "ENV_SECRET_MAPPINGS",
    "SecretScope",
    "get_env_secret_mapping",
]
