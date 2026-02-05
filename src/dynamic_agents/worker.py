"""Redis Stream worker responsible for executing agent requests."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import socket
from collections.abc import Awaitable, Callable, Iterable, Mapping
from contextlib import suppress
from typing import cast
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from dynamic_agents.api.deps import (
    get_agent_factory,
    get_agent_repository,
    get_execution_engine,
)
from dynamic_agents.core.events import AgentRepository as RouterAgentRepository, EventRouter
from dynamic_agents.core.repository import AgentRepository as CoreAgentRepository
from dynamic_agents.schemas.events import AgentRequestEvent
from dynamic_agents.storage.database import init_db
from typing_extensions import override

logger = logging.getLogger(__name__)

DEFAULT_STREAM_KEY = "events:agent_requests"
DEFAULT_GROUP = "agent-request-workers"
DLQ_SUFFIX = ":dlq"


def _create_redis_client(redis_url: str, *, encoding: str, decode_responses: bool) -> Redis:
    return Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
        redis_url,
        encoding=encoding,
        decode_responses=decode_responses,
    )


class AgentRepositoryAdapter(RouterAgentRepository):
    """Adapter that fulfills EventRouter's repository protocol."""

    def __init__(self, repository: CoreAgentRepository) -> None:
        self._repository: CoreAgentRepository = repository

    @override
    async def get_default_route(self, source: str) -> tuple[str, UUID] | None:
        handler: Callable[[str], Awaitable[tuple[str, UUID] | None]] | None = getattr(
            self._repository, "get_default_route", None
        )
        if handler is None:
            return None
        return await handler(source)


class EventWorker:
    """Consume AgentRequestEvent entries from Redis Streams."""

    def __init__(
        self,
        redis_url: str,
        stream_key: str,
        group: str,
        consumer: str,
        *,
        batch_size: int = 8,
        block_ms: int = 5000,
    ) -> None:
        self.redis_url: str = redis_url
        self.stream_key: str = stream_key
        self.group: str = group
        self.consumer: str = consumer
        self.batch_size: int = batch_size
        self.block_ms: int = block_ms

        self._redis: Redis | None = None
        self._router: EventRouter | None = None
        self._stop_event: asyncio.Event = asyncio.Event()

    async def run(self) -> None:
        """Initialize dependencies and process events until shutdown."""

        await self._initialize()

        try:
            while not self._stop_event.is_set():
                entries = await self._read_batch()
                if not entries:
                    continue
                await self._process_entries(entries)
        except asyncio.CancelledError:  # pragma: no cover - cooperative cancellation
            raise
        finally:
            await self._close()

    def request_shutdown(self) -> None:
        """Signal the worker loop to stop."""

        self._stop_event.set()

    async def _initialize(self) -> None:
        """Prepare Redis client, database, and routing dependencies."""

        await init_db()

        repo = get_agent_repository()
        agent_factory = await get_agent_factory(repo)
        execution_engine = await get_execution_engine(agent_factory)
        self._router = EventRouter(execution_engine, AgentRepositoryAdapter(repo))

        self._redis = _create_redis_client(
            self.redis_url,
            encoding="utf-8",
            decode_responses=False,
        )
        await self._ensure_consumer_group()

    async def _read_batch(self) -> list[tuple[str, list[tuple[str, dict[bytes, bytes]]]]]:
        assert self._redis is not None

        try:
            return cast(
                list[tuple[str, list[tuple[str, dict[bytes, bytes]]]]],
                await self._redis.xreadgroup(
                    groupname=self.group,
                    consumername=self.consumer,
                    streams={self.stream_key: ">"},
                    count=self.batch_size,
                    block=self.block_ms,
                ),
            )
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to read from stream", extra={"stream": self.stream_key})
            await asyncio.sleep(1.0)
            return []

    async def _process_entries(
        self,
        entries: Iterable[tuple[str, list[tuple[str, dict[bytes, bytes]]]]],
    ) -> None:
        assert self._router is not None and self._redis is not None

        for stream_name, messages in entries:
            for message_id, payload in messages:
                try:
                    event = self._deserialize_event(payload)
                except Exception as exc:
                    await self._handle_failure(message_id, payload, exc, stream_name)
                    continue

                try:
                    _ = await self._router.handle_event(event)
                except Exception as exc:
                    await self._handle_failure(message_id, payload, exc, stream_name)
                else:
                    await self._ack(message_id)

    async def _handle_failure(
        self,
        message_id: str,
        payload: dict[bytes, bytes],
        exc: Exception,
        stream_name: str,
    ) -> None:
        assert self._redis is not None

        logger.exception(
            "Failed to process event",
            extra={"stream": stream_name, "message_id": message_id},
        )

        dlq_stream = f"{self.stream_key}{DLQ_SUFFIX}"
        serialized_payload = json.dumps(self._decode_fields(payload), default=str)

        try:
            await self._redis.xadd(
                dlq_stream,
                {
                    "message_id": message_id,
                    "stream": stream_name,
                    "error": str(exc),
                    "payload": serialized_payload,
                },
            )
        except Exception:  # pragma: no cover - logging only
            logger.exception("Failed to publish to DLQ", extra={"stream": dlq_stream})

        await self._ack(message_id)

    async def _ack(self, message_id: str) -> None:
        assert self._redis is not None

        try:
            await self._redis.xack(self.stream_key, self.group, message_id)
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to ack message", extra={"message_id": message_id})

    def _deserialize_event(self, payload: dict[bytes, bytes]) -> AgentRequestEvent:
        decoded = self._decode_fields(payload)

        raw_candidate: object
        if "event" in decoded:
            raw_candidate = self._maybe_load_json(decoded["event"])
        elif "data" in decoded:
            raw_candidate = self._maybe_load_json(decoded["data"])
        elif len(decoded) == 1:
            raw_candidate = self._maybe_load_json(next(iter(decoded.values())))
        else:
            raw_candidate = decoded

        if not isinstance(raw_candidate, Mapping):
            raise ValueError("Event payload must decode to a mapping")

        mapping_candidate = cast(Mapping[str, object], raw_candidate)
        normalized: dict[str, object] = {
            key: self._maybe_load_json(value) for key, value in mapping_candidate.items()
        }

        return AgentRequestEvent.model_validate(normalized)

    @staticmethod
    def _decode_fields(payload: dict[bytes, bytes]) -> dict[str, str]:
        return {EventWorker._decode(k): EventWorker._decode(v) for k, v in payload.items()}

    @staticmethod
    def _decode(value: bytes | str) -> str:
        if isinstance(value, bytes):
            return value.decode()
        return value

    @staticmethod
    def _maybe_load_json(value: object) -> object:
        if isinstance(value, str):
            candidate = value.strip()
            if candidate and candidate[0] in '[{"':
                try:
                    return cast(object, json.loads(candidate))
                except json.JSONDecodeError:
                    return value
        return value

    async def _ensure_consumer_group(self) -> None:
        assert self._redis is not None

        try:
            await self._redis.xgroup_create(
                name=self.stream_key,
                groupname=self.group,
                id="0-0",
                mkstream=True,
            )
            logger.info(
                "Created consumer group",
                extra={"stream": self.stream_key, "group": self.group},
            )
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def _close(self) -> None:
        if self._redis is not None:
            await self._redis.close()
            self._redis = None


async def main() -> None:
    log_level_name = os.getenv("WORKER_LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    logging.basicConfig(level=log_level)

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    stream_key = os.getenv("REDIS_STREAM_KEY", DEFAULT_STREAM_KEY)
    group = os.getenv("REDIS_CONSUMER_GROUP", DEFAULT_GROUP)
    consumer = os.getenv(
        "REDIS_CONSUMER_NAME",
        f"{socket.gethostname()}-{os.getpid()}",
    )

    worker = EventWorker(redis_url, stream_key, group, consumer)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, worker.request_shutdown)

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
