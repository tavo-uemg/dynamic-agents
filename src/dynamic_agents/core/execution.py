"""Execution engine responsible for orchestrating agent runs."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, AsyncIterator, Awaitable, Callable, Optional, Protocol, cast
from types import TracebackType
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models import ExecutionRecord, ExecutionStatus, ExecutionTargetType
from ..schemas.events import AgentRequestEvent, AgentResponseEvent
from ..schemas.executions import ExecutionResult as ExecutionSchema

if TYPE_CHECKING:
    from .team_factory import TeamFactory
    from .workflow_factory import WorkflowFactory


class AsyncSessionContext(Protocol):
    async def __aenter__(self) -> AsyncSession: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool: ...


SessionFactory = Callable[[], AsyncSessionContext]


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
        session_factory: SessionFactory,
        team_factory: Optional["TeamFactory"] = None,
        workflow_factory: Optional["WorkflowFactory"] = None,
    ) -> None:
        self._factory: AgentFactory = agent_factory
        self._session_factory: SessionFactory = session_factory
        self._team_factory: Optional[TeamFactory] = team_factory
        self._workflow_factory: Optional[WorkflowFactory] = workflow_factory

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

        return await self._run_target(
            target_type=ExecutionTargetType.AGENT,
            target_id=agent_id,
            input_text=input_text,
            session_id=session_id,
            user_id=user_id,
            metadata=metadata,
            stream=stream,
            resolver=self._factory.get_agent,
        )

    async def run_team(
        self,
        team_id: UUID,
        input_text: str,
        session_id: str | None = None,
        user_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        stream: bool = False,
    ) -> ExecutionSchema:
        """Execute a team and persist the result."""

        if self._team_factory is None:
            raise ValueError("TeamFactory is not configured for this ExecutionEngine")

        return await self._run_target(
            target_type=ExecutionTargetType.TEAM,
            target_id=team_id,
            input_text=input_text,
            session_id=session_id,
            user_id=user_id,
            metadata=metadata,
            stream=stream,
            resolver=self._team_factory.get_team,
        )

    async def run_workflow(
        self,
        workflow_id: UUID,
        input_text: str,
        session_id: str | None = None,
        user_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        stream: bool = False,
    ) -> ExecutionSchema:
        """Execute a workflow and persist the result."""

        if self._workflow_factory is None:
            raise ValueError("WorkflowFactory is not configured for this ExecutionEngine")

        return await self._run_target(
            target_type=ExecutionTargetType.WORKFLOW,
            target_id=workflow_id,
            input_text=input_text,
            session_id=session_id,
            user_id=user_id,
            metadata=metadata,
            stream=stream,
            resolver=self._workflow_factory.get_workflow,
        )

    async def run_from_event(self, event: AgentRequestEvent) -> AgentResponseEvent:
        """Process an event from Redis Streams."""

        payload = event.payload or {}
        metadata = dict(event.metadata or {})
        stream = bool(metadata.pop("stream", False))
        metadata.setdefault("request_event_id", event.event_id)

        input_text = self._extract_input_text(payload)
        target_type, target_id = self._resolve_event_target(event)

        if target_type is ExecutionTargetType.AGENT:
            execution = await self.run_agent(
                target_id,
                input_text,
                session_id=event.session_id,
                user_id=event.user_id,
                metadata=metadata,
                stream=stream,
            )
        elif target_type is ExecutionTargetType.TEAM:
            execution = await self.run_team(
                target_id,
                input_text,
                session_id=event.session_id,
                user_id=event.user_id,
                metadata=metadata,
                stream=stream,
            )
        else:
            execution = await self.run_workflow(
                target_id,
                input_text,
                session_id=event.session_id,
                user_id=event.user_id,
                metadata=metadata,
                stream=stream,
            )

        metadata["target_type"] = target_type.value
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

    async def _run_target(
        self,
        target_type: ExecutionTargetType,
        target_id: UUID,
        input_text: str,
        session_id: str | None,
        user_id: UUID | None,
        metadata: dict[str, Any] | None,
        stream: bool,
        resolver: Callable[[UUID], Awaitable[Any]],
    ) -> ExecutionSchema:
        metadata = dict(metadata or {})
        input_payload = {
            "content": input_text,
            "metadata": metadata,
        }

        record = await self._create_execution_record(
            target_type,
            target_id,
            input_payload,
            user_id,
            session_id,
        )

        started_at = datetime.now(timezone.utc)
        execution_id = cast(UUID, cast(Any, record.id))
        await self._mark_execution_running(execution_id, started_at)

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
            runnable = cast(RunnableAgent, await resolver(target_id))
            kwargs = self._build_agent_kwargs(session_id, user_id, metadata)
            if stream:
                output_payload, tokens = await self._run_runnable_stream(
                    runnable, input_text, kwargs
                )
            else:
                output_payload, tokens = await self._run_runnable_once(runnable, input_text, kwargs)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception(
                "%s execution failed",
                target_type.value.capitalize(),
                extra={
                    "target_type": target_type.value,
                    "target_id": str(target_id),
                    "execution_id": str(execution_id),
                },
            )
            error_message = str(exc)
        finally:
            duration_ms = (loop.time() - start_time) * 1000.0

        if error_message is None:
            await self._update_execution_success(execution_id, output_payload, duration_ms, tokens)
        else:
            await self._update_execution_failure(execution_id, error_message, duration_ms)

        return await self._fetch_execution_result(execution_id)

    async def _run_runnable_once(
        self,
        agent: RunnableAgent,
        input_text: str,
        kwargs: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, int] | None]:
        response = await agent.arun(input_text, **kwargs)
        return self._normalize_output(response)

    async def _run_runnable_stream(
        self,
        agent: RunnableAgent,
        input_text: str,
        kwargs: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, int] | None]:
        stream_callable = getattr(agent, "arun_stream", None)
        if stream_callable is None:
            return await self._run_runnable_once(agent, input_text, kwargs)

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
        input_payload: dict[str, Any],
        user_id: UUID | None,
        session_id: str | None,
    ) -> ExecutionRecord:
        """Create initial execution record."""

        record: ExecutionRecord | None = None
        session_ctx = self._session_factory()
        async with session_ctx as session:
            session_any = cast(Any, session)
            record_any: Any = ExecutionRecord.__new__(ExecutionRecord)
            record_any.target_type = target_type
            record_any.status = ExecutionStatus.PENDING
            record_any.agent_id = target_id if target_type == ExecutionTargetType.AGENT else None
            record_any.team_id = target_id if target_type == ExecutionTargetType.TEAM else None
            record_any.workflow_id = (
                target_id if target_type == ExecutionTargetType.WORKFLOW else None
            )
            record_any.session_id = session_id
            record_any.user_id = user_id
            record_any.input_payload = input_payload
            record_any.run_metadata = dict(input_payload.get("metadata") or {})

            record = cast(ExecutionRecord, record_any)
            session_any.add(record)
            await session_any.commit()
            await session_any.refresh(record)
        if record is None:
            raise RuntimeError("Execution record was not created")
        return record

    async def _mark_execution_running(self, execution_id: UUID, started_at: datetime) -> None:
        session_ctx = self._session_factory()
        async with session_ctx as session:
            session_any = cast(Any, session)
            record = await session_any.get(ExecutionRecord, execution_id)
            if record is None:
                return
            record.status = ExecutionStatus.RUNNING
            record.started_at = started_at
            await session_any.commit()

    async def _update_execution_success(
        self,
        execution_id: UUID,
        output: dict[str, Any],
        duration_ms: float,
        tokens: dict[str, int] | None,
    ) -> None:
        """Mark execution as completed."""

        session_ctx = self._session_factory()
        async with session_ctx as session:
            session_any = cast(Any, session)
            record = await session_any.get(ExecutionRecord, execution_id)
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
            await session_any.commit()

    async def _update_execution_failure(
        self,
        execution_id: UUID,
        error: str,
        duration_ms: float,
    ) -> None:
        """Mark execution as failed."""

        session_ctx = self._session_factory()
        async with session_ctx as session:
            session_any = cast(Any, session)
            record = await session_any.get(ExecutionRecord, execution_id)
            if record is None:
                return
            record.status = ExecutionStatus.FAILED
            record.error_message = error
            record.duration_ms = duration_ms
            record.finished_at = datetime.now(timezone.utc)
            await session_any.commit()

    async def _fetch_execution_result(self, execution_id: UUID) -> ExecutionSchema:
        record: ExecutionRecord | None = None
        session_ctx = self._session_factory()
        async with session_ctx as session:
            session_any = cast(Any, session)
            record = await session_any.get(ExecutionRecord, execution_id)
            if record is None:
                raise ValueError(f"Execution {execution_id} not found")
            await session_any.refresh(record)
        if record is None:
            raise RuntimeError("Execution record could not be loaded")
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

    def _resolve_event_target(self, event: AgentRequestEvent) -> tuple[ExecutionTargetType, UUID]:
        agent_id = getattr(event, "agent_id", None)
        if isinstance(agent_id, UUID):
            return (ExecutionTargetType.AGENT, agent_id)

        metadata = event.metadata or {}
        payload = event.payload or {}
        lookup_order = (
            ("team_id", ExecutionTargetType.TEAM),
            ("workflow_id", ExecutionTargetType.WORKFLOW),
            ("agent_id", ExecutionTargetType.AGENT),
        )

        for key, target_type in lookup_order:
            candidate = metadata.get(key) or payload.get(key)
            parsed = self._maybe_uuid(candidate)
            if parsed is not None:
                return (target_type, parsed)

        raise ValueError(
            "AgentRequestEvent must define agent_id, team_id, or workflow_id for execution"
        )

    @staticmethod
    def _maybe_uuid(value: Any) -> UUID | None:
        if isinstance(value, UUID):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            try:
                return UUID(stripped)
            except (TypeError, ValueError):
                return None
        return None


__all__ = ["ExecutionEngine", "AgentFactory", "RunnableAgent", "AgentRunOutput"]
