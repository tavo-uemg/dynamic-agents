"""Declarative base configuration, shared mixins, and custom column types."""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID, uuid4

from sqlalchemy import DateTime, MetaData, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import CHAR, JSON, TypeDecorator


naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class GUID(TypeDecorator[UUID]):
    """Platform-independent UUID column supporting PostgreSQL and SQLite."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[override]
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: UUID | str | None, dialect):  # type: ignore[override]
        if value is None:
            return value
        if isinstance(value, UUID):
            return str(value)
        return str(UUID(str(value)))

    def process_result_value(self, value: str | UUID | None, dialect):  # type: ignore[override]
        if value is None:
            return value
        if isinstance(value, UUID):
            return value
        return UUID(str(value))


class JSONBType(TypeDecorator[Any]):
    """JSON column that upgrades to JSONB when PostgreSQL is available."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[override]
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import JSONB

            return dialect.type_descriptor(JSONB(astext_type=Text()))
        return dialect.type_descriptor(JSON())


class Base(DeclarativeBase):
    """Declarative base class that wires custom naming conventions and types."""

    metadata = MetaData(naming_convention=naming_convention)
    type_annotation_map: ClassVar[dict[type[Any], Any]] = {
        dict[str, Any]: JSONBType,
        list[str]: JSONBType,
        list[dict[str, Any]]: JSONBType,
    }


class UUIDPrimaryKey:
    """Mixin providing a UUID primary key column."""

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)


class TimestampMixin:
    """Mixin adding creation and update timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UserOwnedMixin:
    """Mixin that stores the owner/tenant identifier for row scoping."""

    user_id: Mapped[UUID | None] = mapped_column(GUID(), index=True, nullable=True)


__all__ = [
    "Base",
    "GUID",
    "JSONBType",
    "TimestampMixin",
    "UUIDPrimaryKey",
    "UserOwnedMixin",
]
