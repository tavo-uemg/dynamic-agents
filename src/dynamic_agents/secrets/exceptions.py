"""Custom exceptions used by the secrets integration layer."""

from __future__ import annotations


class SecretsManagerError(Exception):
    """Base error raised for any secrets related issue."""


class SecretsConfigError(SecretsManagerError):
    """Raised when the manager is misconfigured or missing credentials."""


class SecretsAPIError(SecretsManagerError):
    """Raised when the Identity API returns an unexpected response."""


class SecretsAuthError(SecretsAPIError):
    """Raised when authentication with the Identity API fails."""


class SecretsUnavailableError(SecretsManagerError):
    """Raised when the Identity API cannot be reached."""


class SecretNotFoundError(SecretsManagerError):
    """Raised when the requested provider or field is unknown."""


__all__ = [
    "SecretNotFoundError",
    "SecretsAPIError",
    "SecretsAuthError",
    "SecretsConfigError",
    "SecretsManagerError",
    "SecretsUnavailableError",
]
