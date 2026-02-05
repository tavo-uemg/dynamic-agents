"""Shared Pydantic schemas and utilities."""

from __future__ import annotations

from datetime import datetime
from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

JSONValue = Any
Metadata = dict[str, Any]


class ORMModel(BaseModel):
    """Base model configured for ORM serialization."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TimestampedSchema(ORMModel):
    """Schema containing common timestamp fields."""

    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class IdentifiedSchema(TimestampedSchema):
    """Schema exposing the primary identifier field."""

    id: UUID


__all__ = [
    "IdentifiedSchema",
    "JSONValue",
    "Metadata",
    "ORMModel",
    "TimestampedSchema",
]
