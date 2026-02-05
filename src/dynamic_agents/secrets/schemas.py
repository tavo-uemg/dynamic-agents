"""Pydantic schemas mirroring responses from the A8N Identity API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SecretMetadata(BaseModel):
    """Metadata about a stored secret returned by the Identity service."""

    id: str
    name: str
    provider: str
    status: str | None = None
    type: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    fields: dict[str, Any] = Field(default_factory=dict)


class SecretListResponse(BaseModel):
    """Wrapper for ``GET /api/v1/secrets`` responses."""

    items: list[SecretMetadata] | None = None

    def as_list(self) -> list[SecretMetadata]:
        """Return the contained items as a list regardless of payload shape."""

        if self.items is None:
            return []
        return self.items


class SecretWithValues(BaseModel):
    """Decrypted secret payload returned by ``/values`` endpoints."""

    id: str
    name: str
    provider: str
    values: dict[str, str] = Field(default_factory=dict)


__all__ = [
    "SecretMetadata",
    "SecretListResponse",
    "SecretWithValues",
]
