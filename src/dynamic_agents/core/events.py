"""Event routing utilities for dynamic agent execution."""

from __future__ import annotations

import re
from typing import Any, Literal, Protocol
from uuid import UUID

from ..schemas.base import ORMModel
from ..schemas.events import AgentRequestEvent, AgentResponseEvent
from .execution import ExecutionEngine


class AgentRepository(Protocol):
    """Repository interface used to discover available agents."""

    async def get_default_route(self, source: str) -> tuple[str, UUID] | None: ...


class EventRouter:
    """Routes incoming events to appropriate handlers."""

    def __init__(
        self,
        execution_engine: ExecutionEngine,
        agent_repository: AgentRepository,
    ) -> None:
        self._engine = execution_engine
        self._agent_repo = agent_repository
        self._routing_rules: list[RoutingRule] = []

    async def route(self, event: AgentRequestEvent) -> tuple[str, UUID]:
        """Determine which agent/team/workflow should handle the event."""

        explicit_target = self._extract_explicit_target(event)
        if explicit_target:
            return explicit_target

        for rule in sorted(self._routing_rules, key=lambda rule: rule.priority, reverse=True):
            if rule.matches(event):
                return (rule.target_type, rule.target_id)

        source = self._extract_source(event)
        if source:
            repo_handler = getattr(self._agent_repo, "get_default_route", None)
            if repo_handler is not None:
                fallback = await repo_handler(source)
                if fallback:
                    return fallback

        raise ValueError("No routing target available for event")

    async def handle_event(self, event: AgentRequestEvent) -> AgentResponseEvent:
        """Process an incoming event and return response."""

        target_type, target_id = await self.route(event)
        if target_type != "agent":
            raise NotImplementedError(f"Routing for target type '{target_type}' is not supported")

        routed_event = (
            event
            if event.agent_id == target_id
            else event.model_copy(update={"agent_id": target_id})
        )
        return await self._engine.run_from_event(routed_event)

    def add_routing_rule(self, rule: RoutingRule) -> None:
        """Add a routing rule."""

        self._routing_rules.append(rule)

    def _extract_explicit_target(self, event: AgentRequestEvent) -> tuple[str, UUID] | None:
        if event.agent_id:
            return ("agent", event.agent_id)

        metadata = event.metadata or {}
        payload = event.payload or {}

        team_id = metadata.get("team_id") or payload.get("team_id")
        if isinstance(team_id, UUID):
            return ("team", team_id)

        workflow_id = metadata.get("workflow_id") or payload.get("workflow_id")
        if isinstance(workflow_id, UUID):
            return ("workflow", workflow_id)

        agent_id = metadata.get("agent_id") or payload.get("agent_id")
        if isinstance(agent_id, UUID):
            return ("agent", agent_id)

        return None

    def _extract_source(self, event: AgentRequestEvent) -> str | None:
        metadata = event.metadata or {}
        payload = event.payload or {}
        source = metadata.get("source") or payload.get("source")
        if isinstance(source, str) and source:
            return source
        return None


class RoutingRule(ORMModel):
    """Rule for routing events to handlers."""

    name: str
    priority: int = 0

    source_pattern: str | None = None
    content_pattern: str | None = None
    user_pattern: str | None = None

    target_type: Literal["agent", "team", "workflow"]
    target_id: UUID

    def matches(self, event: AgentRequestEvent) -> bool:
        metadata = event.metadata or {}
        payload = event.payload or {}

        if self.source_pattern:
            source_value = metadata.get("source") or payload.get("source") or ""
            if not self._match_pattern(self.source_pattern, source_value):
                return False

        if self.content_pattern:
            content_value = payload.get("content") or payload.get("input_text") or ""
            if not self._match_pattern(self.content_pattern, content_value):
                return False

        if self.user_pattern:
            user_value = str(event.user_id or metadata.get("user_id") or "")
            if not self._match_pattern(self.user_pattern, user_value):
                return False

        return True

    @staticmethod
    def _match_pattern(pattern: str, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return re.search(pattern, value) is not None


__all__ = ["AgentRepository", "EventRouter", "RoutingRule"]
