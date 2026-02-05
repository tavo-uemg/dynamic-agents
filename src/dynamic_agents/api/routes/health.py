"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from ..deps import DbSession

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return a simple service health indicator."""

    return {"status": "healthy"}


@router.get("/health/ready")
async def readiness_check(db: DbSession) -> dict[str, str]:
    """Ensure the database connection is ready to accept queries."""

    await db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "connected"}


__all__ = ["router"]
