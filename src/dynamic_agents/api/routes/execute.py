"""Agent execution endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ...schemas import ExecutionResult
from ..deps import ExecutionEngineDep

router = APIRouter()


class ExecuteRequest(BaseModel):
    """Payload for triggering agent executions."""

    input: str = Field(..., description="The input text provided to the agent")
    session_id: str | None = Field(default=None, description="Optional session identifier")
    metadata: dict[str, Any] | None = Field(default=None, description="Custom metadata context")
    stream: bool = Field(default=False, description="Request streaming execution when supported")


@router.post("/agent/{agent_id}", response_model=ExecutionResult)
async def execute_agent(
    agent_id: UUID,
    request: ExecuteRequest,
    engine: ExecutionEngineDep,
) -> ExecutionResult:
    """Execute an agent and return the persisted execution record."""

    try:
        result = await engine.run_agent(
            agent_id=agent_id,
            input_text=request.input,
            session_id=request.session_id,
            metadata=request.metadata,
            stream=request.stream,
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent execution failed",
        ) from exc
    return result


__all__ = ["router", "ExecuteRequest"]
