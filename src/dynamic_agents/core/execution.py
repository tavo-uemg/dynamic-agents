"""Execution engine responsible for orchestrating agent runs."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models import ExecutionRecord, ExecutionStatus, ExecutionTargetType
from ..schemas.events import AgentRequestEvent, AgentResponseEvent
from ..schemas.executions import ExecutionResult as ExecutionSchema


logger = logging.getLogger(__name__)


class RunnableAgent(Protocol):
    """Minimal async interface expected from runtime agents."""

    async def arun(self, input_text: str, /, **kwargs: Any) -> Any: ...

    def arun_stream(self, input_text: str, /, **kwargs: Any) -> AsyncIterator[Any]: ...


class AgentFactory(Protocol):
    """Factory responsible for returning concrete agent instances."""

    async def get_agent(self, agent_id: UUID) -> RunnableAgent: ...


@dataclass
class AgentRunOutput:
    """Normalized representation of an agent response."""

    content: str | None = None
    structured_data: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    tokens: dict[str, int] | None = None

    @classmethod
    def from_value(cls, value: Any) -> "AgentRunOutput":
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(content=value, metadata={})
        if isinstance(value, dict):
            metadata = value.get("metadata") or {}
            tokens = value.get("tokens")
            structured = value.get("structured_data")
            content = value.get("content") or value.get("text")
            return cls(
                content=content,
                structured_data=structured,
                metadata=metadata,
                tokens=tokens,
            )
        if value is None:
            return cls(metadata={})
        return cls(content=str(value), metadata={})


class ExecutionEngine:
    """Manages agent/team/workflow execution with persistence."""

    def __init__(
        self,
        agent_factory: AgentFactory,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._factory = agent_factory
        self._session_factory = session_factory

    async def run_agent(
        self,
        agent_id: UUID,
        input_text: str,
        session_id: str | None = None,
        user_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        stream: bool = False,
    ) -> ExecutionSchema:
        """Execute an agent and persist the result."""

        metadata = dict(metadata or {})
        input_payload = {
            "content": input_text,
            "metadata": metadata,
        }

        record = await self._create_execution_record(
            ExecutionTargetType.AGENT,
            agent_id,
            input_payload,
            user_id,
            session_id,
        )

        started_at = datetime.now(timezone.utc)
        await self._mark_execution_running(record.id, started_at)

        loop = asyncio.get_running_loop()
        start_time = loop.time()
        duration_ms: float
        error_message: str | None = None
        tokens: dict[str, int] | None = None
        output_payload: dict[str, Any] = {
            "content": None,
            "structured_data": None,
            "metadata": {},
        }

        try:
            agent = await self._factory.get_agent(agent_id)
            kwargs = self._build_agent_kwargs(session_id, user_id, metadata)
            if stream:
                output_payload, tokens = await self._run_agent_stream(agent, input_text, kwargs)
            else:
                output_payload, tokens = await self._run_agent_once(agent, input_text, kwargs)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception(
                "Agent execution failed",
                extra={"agent_id": str(agent_id), "execution_id": str(record.id)},
            )
            error_message = str(exc)
        finally:
            duration_ms = (loop.time() - start_time) * 1000.0

        if error_message is None:
            await self._update_execution_success(record.id, output_payload, duration_ms, tokens)
        else:
            await self._update_execution_failure(record.id, error_message, duration_ms)

        return await self._fetch_execution_result(record.id)

    async def run_from_event(self, event: AgentRequestEvent) -> AgentResponseEvent:
        """Process an event from Redis Streams."""

        if not event.agent_id:
            raise ValueError("AgentRequestEvent must define agent_id for execution")

        payload = event.payload or {}
        metadata = dict(event.metadata or {})
        stream = bool(metadata.pop("stream", False))
        metadata.setdefault("request_event_id", event.event_id)

        input_text = self._extract_input_text(payload)
        execution = await self.run_agent(
            event.agent_id,
            input_text,
            session_id=event.session_id,
            user_id=event.user_id,
            metadata=metadata,
            stream=stream,
        )
        response_metadata = dict(metadata)
        response_metadata.update(execution.run_metadata or {})

        tokens_payload = self._tokens_from_execution(execution)

        return AgentResponseEvent(
            execution_id=execution.id,
            status=execution.status,
            output=execution.output_payload,
            error=execution.error_message,
            tokens=tokens_payload,
            metadata=response_metadata,
        )

    async def _run_agent_once(
        self,
        agent: RunnableAgent,
        input_text: str,
        kwargs: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, int] | None]:
        response = await agent.arun(input_text, **kwargs)
        return self._normalize_output(response)

    async def _run_agent_stream(
        self,
        agent: RunnableAgent,
        input_text: str,
        kwargs: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, int] | None]:
        stream_callable = getattr(agent, "arun_stream", None)
        if stream_callable is None:
            return await self._run_agent_once(agent, input_text, kwargs)

        stream_result = stream_callable(input_text, **kwargs)
        final_chunk: Any = None

        if hasattr(stream_result, "__aiter__"):
            async for chunk in stream_result:
                final_chunk = chunk
        else:
            final_chunk = await stream_result

        return self._normalize_output(final_chunk)

    def _normalize_output(self, raw_output: Any) -> tuple[dict[str, Any], dict[str, int] | None]:
        normalized = AgentRunOutput.from_value(raw_output)
        metadata = dict(normalized.metadata or {})
        payload = {
            "content": normalized.content,
            "structured_data": normalized.structured_data,
            "metadata": metadata,
        }
        return payload, normalized.tokens

    def _build_agent_kwargs(
        self,
        session_id: str | None,
        user_id: UUID | None,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "metadata": metadata,
        }
        if session_id is not None:
            kwargs["session_id"] = session_id
        if user_id is not None:
            kwargs["user_id"] = user_id
        return kwargs

    async def _create_execution_record(
        self,
        target_type: ExecutionTargetType,
        target_id: UUID,
        input_payload: dict,
        user_id: UUID | None,
        session_id: str | None,
    ) -> ExecutionRecord:
        """Create initial execution record."""

        async with self._session_factory() as session:
            record = ExecutionRecord(
                target_type=target_type,
                status=ExecutionStatus.PENDING,
                agent_id=target_id if target_type == ExecutionTargetType.AGENT else None,
                team_id=target_id if target_type == ExecutionTargetType.TEAM else None,
                workflow_id=target_id if target_type == ExecutionTargetType.WORKFLOW else None,
                session_id=session_id,
                user_id=user_id,
                input_payload=input_payload,
                run_metadata=dict(input_payload.get("metadata") or {}),
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record

    async def _mark_execution_running(self, execution_id: UUID, started_at: datetime) -> None:
        async with self._session_factory() as session:
            record = await session.get(ExecutionRecord, execution_id)
            if record is None:
                return
            record.status = ExecutionStatus.RUNNING
            record.started_at = started_at
            await session.commit()

    async def _update_execution_success(
        self,
        execution_id: UUID,
        output: dict,
        duration_ms: float,
        tokens: dict[str, int] | None,
    ) -> None:
        """Mark execution as completed."""

        async with self._session_factory() as session:
            record = await session.get(ExecutionRecord, execution_id)
            if record is None:
                return
            record.status = ExecutionStatus.COMPLETED
            record.output_payload = output
            record.duration_ms = duration_ms
            record.finished_at = datetime.now(timezone.utc)
            record.error_message = None
            if tokens:
                record.prompt_tokens = tokens.get("prompt_tokens")
                record.completion_tokens = tokens.get("completion_tokens")
                record.total_tokens = tokens.get("total_tokens")
            await session.commit()

    async def _update_execution_failure(
        self,
        execution_id: UUID,
        error: str,
        duration_ms: float,
    ) -> None:
        """Mark execution as failed."""

        async with self._session_factory() as session:
            record = await session.get(ExecutionRecord, execution_id)
            if record is None:
                return
            record.status = ExecutionStatus.FAILED
            record.error_message = error
            record.duration_ms = duration_ms
            record.finished_at = datetime.now(timezone.utc)
            await session.commit()

    async def _fetch_execution_result(self, execution_id: UUID) -> ExecutionSchema:
        async with self._session_factory() as session:
            record = await session.get(ExecutionRecord, execution_id)
            if record is None:
                raise ValueError(f"Execution {execution_id} not found")
            await session.refresh(record)
            return ExecutionSchema.model_validate(record)

    def _extract_input_text(self, payload: dict[str, Any]) -> str:
        for key in ("content", "input_text", "text", "message"):
            value = payload.get(key)
            if isinstance(value, str):
                return value
        return ""

    def _tokens_from_execution(self, execution: ExecutionSchema) -> dict[str, int]:
        tokens: dict[str, int] = {}
        if execution.prompt_tokens is not None:
            tokens["prompt_tokens"] = execution.prompt_tokens
        if execution.completion_tokens is not None:
            tokens["completion_tokens"] = execution.completion_tokens
        if execution.total_tokens is not None:
            tokens["total_tokens"] = execution.total_tokens
        return tokens


__all__ = ["ExecutionEngine", "AgentFactory", "RunnableAgent", "AgentRunOutput"]
