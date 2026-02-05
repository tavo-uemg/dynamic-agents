"""Factory responsible for preparing workflow configurations for execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence
from uuid import UUID

from ..models import WorkflowModel
from ..schemas import StepConfig, WorkflowConfig
from .exceptions import AgentFactoryError, AgentNotFoundError
from .factory import AgentFactory
from .team_factory import TeamFactory, TeamFactoryError
from .workflow_repository import WorkflowRepository

__all__ = [
    "AgnoWorkflow",
    "ResolvedWorkflow",
    "ResolvedWorkflowStep",
    "WorkflowFactory",
    "WorkflowFactoryError",
    "WorkflowNotFoundError",
]


class WorkflowFactoryError(AgentFactoryError):
    """Raised when a workflow cannot be assembled or configured."""


class WorkflowNotFoundError(WorkflowFactoryError, AgentNotFoundError):
    """Raised when a requested workflow configuration cannot be located."""


@dataclass
class ResolvedWorkflowStep:
    """Runtime-ready workflow step with resolved executor references."""

    name: str
    type: str
    executor_id: str | None
    executor: Any | None
    condition: str | None
    loop_condition: str | None
    parallel_steps: list["ResolvedWorkflowStep"]


@dataclass
class ResolvedWorkflow:
    """Runtime-ready workflow structure returned by the factory."""

    name: str
    description: str | None
    status: Any
    steps: list[ResolvedWorkflowStep]
    input_schema: str | None
    add_workflow_history_to_steps: bool
    stream_executor_events: bool
    tags: list[str]
    metadata: dict[str, Any]
    user_id: UUID | None
    id: UUID | None = None


AgnoWorkflow = ResolvedWorkflow


class WorkflowFactory:
    """Validates and resolves workflow configurations before execution."""

    def __init__(
        self,
        agent_factory: AgentFactory | None = None,
        team_factory: TeamFactory | None = None,
    ) -> None:
        self._agent_factory = agent_factory
        self._team_factory = team_factory
        self._default_repository: WorkflowRepository | None = None

    def bind_repository(self, repository: WorkflowRepository) -> None:
        """Store a default repository used by get_workflow."""

        self._default_repository = repository

    async def get_workflow(self, workflow_id: UUID) -> AgnoWorkflow:
        """Return a resolved workflow using the bound repository."""

        if self._default_repository is None:
            raise WorkflowFactoryError(
                "WorkflowRepository has not been configured for this factory"
            )
        return await self.create_from_id(workflow_id, self._default_repository)

    async def create_from_config(self, config: WorkflowConfig) -> AgnoWorkflow:
        """Return a resolved workflow for the supplied configuration."""

        steps = await self._resolve_steps(config.steps)
        return ResolvedWorkflow(
            name=config.name,
            description=config.description,
            status=config.status,
            steps=steps,
            input_schema=config.input_schema,
            add_workflow_history_to_steps=config.add_workflow_history_to_steps,
            stream_executor_events=config.stream_executor_events,
            tags=list(config.tags),
            metadata=dict(config.metadata or {}),
            user_id=config.user_id,
        )

    async def create_from_id(
        self,
        workflow_id: UUID,
        repository: WorkflowRepository,
    ) -> AgnoWorkflow:
        """Load config from repository and return resolved workflow."""

        model = await repository.get(workflow_id)
        if model is None:
            raise WorkflowNotFoundError(f"Workflow '{workflow_id}' was not found")

        config = _model_to_workflow_config(model)
        workflow = await self.create_from_config(config)
        workflow.id = workflow_id
        return workflow

    async def _resolve_steps(self, steps: Sequence[StepConfig]) -> list[ResolvedWorkflowStep]:
        resolved: list[ResolvedWorkflowStep] = []
        for step in steps:
            executor = await self._resolve_executor(step)
            parallel_steps: list[ResolvedWorkflowStep] = []
            if step.parallel_steps:
                parallel_steps = await self._resolve_steps(step.parallel_steps)

            resolved.append(
                ResolvedWorkflowStep(
                    name=step.name,
                    type=step.type,
                    executor_id=step.executor_id,
                    executor=executor,
                    condition=step.condition,
                    loop_condition=step.loop_condition,
                    parallel_steps=parallel_steps,
                )
            )
        return resolved

    async def _resolve_executor(self, step: StepConfig) -> Any:
        step_type = step.type
        executor_id = step.executor_id

        if step_type not in {"agent", "team"}:
            return None
        if executor_id is None:
            raise WorkflowFactoryError(f"Step '{step.name}' requires executor_id")

        executor_uuid = _parse_uuid(executor_id, step.name)
        if step_type == "agent":
            if self._agent_factory is None:
                raise WorkflowFactoryError("AgentFactory is required to resolve agent steps")
            return await self._agent_factory.get_agent(executor_uuid)

        if self._team_factory is None:
            raise WorkflowFactoryError("TeamFactory is required to resolve team steps")
        try:
            return await self._team_factory.get_team(executor_uuid)
        except TeamFactoryError as exc:
            raise WorkflowFactoryError(str(exc)) from exc


def _parse_uuid(raw_id: str, step_name: str) -> UUID:
    try:
        return UUID(raw_id)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise WorkflowFactoryError(
            f"Step '{step_name}' has invalid executor_id '{raw_id}'"
        ) from exc


def _model_to_workflow_config(model: WorkflowModel) -> WorkflowConfig:
    steps_payload = [StepConfig.model_validate(step) for step in model.steps or []]
    return WorkflowConfig(
        name=model.name,
        description=model.description,
        status=model.status,
        steps=steps_payload,
        input_schema=model.input_schema,
        add_workflow_history_to_steps=model.add_workflow_history_to_steps,
        stream_executor_events=model.stream_executor_events,
        tags=list(model.tags or []),
        metadata=dict(model.metadata_ or {}),
        user_id=model.user_id,
    )
