"""Initial database schema."""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

from dynamic_agents.models.base import GUID

# revision identifiers, used by Alembic.
revision: str = "202402050001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


execution_target_enum = sa.Enum(
    "agent",
    "team",
    "workflow",
    "router",
    name="executiontargettype",
)

execution_status_enum = sa.Enum(
    "pending",
    "running",
    "success",
    "failed",
    "cancelled",
    name="executionstatus",
)


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("model_config", sa.JSON(), nullable=False),
        sa.Column("member_ids", sa.JSON(), nullable=False),
        sa.Column("respond_directly", sa.Boolean(), nullable=False),
        sa.Column("delegate_to_all_members", sa.Boolean(), nullable=False),
        sa.Column("share_member_interactions", sa.Boolean(), nullable=False),
        sa.Column("add_team_history_to_members", sa.Boolean(), nullable=False),
        sa.Column("num_team_history_runs", sa.Integer(), nullable=False),
        sa.Column("instructions", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    op.create_index("ix_teams_name", "teams", ["name"], unique=False)

    op.create_table(
        "router_configs",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("routing_strategy", sa.String(length=64), nullable=False),
        sa.Column("num_retries", sa.Integer(), nullable=False),
        sa.Column("timeout", sa.Float(), nullable=False),
        sa.Column("allowed_fails", sa.Integer(), nullable=False),
        sa.Column("cooldown_time", sa.Float(), nullable=False),
        sa.Column("fallbacks", sa.JSON(), nullable=False),
        sa.Column("default_fallbacks", sa.JSON(), nullable=False),
        sa.Column("context_window_fallbacks", sa.JSON(), nullable=False),
        sa.Column("enable_pre_call_checks", sa.Boolean(), nullable=False),
        sa.Column("enable_tag_filtering", sa.Boolean(), nullable=False),
        sa.Column("cache_responses", sa.Boolean(), nullable=False),
        sa.Column("redis_host", sa.String(length=255), nullable=True),
        sa.Column("redis_port", sa.Integer(), nullable=True),
        sa.Column("redis_password", sa.String(length=255), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    op.create_index("ix_router_configs_name", "router_configs", ["name"], unique=True)

    op.create_table(
        "workflows",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("input_schema", sa.String(length=255), nullable=True),
        sa.Column("add_workflow_history_to_steps", sa.Boolean(), nullable=False),
        sa.Column("stream_executor_events", sa.Boolean(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    op.create_index("ix_workflows_name", "workflows", ["name"], unique=False)

    op.create_table(
        "tool_registry",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("toolkit_name", sa.String(length=255), nullable=True),
        sa.Column("toolkit_params", sa.JSON(), nullable=False),
        sa.Column("function_name", sa.String(length=255), nullable=True),
        sa.Column("function_module", sa.String(length=255), nullable=True),
        sa.Column("mcp_server", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    op.create_index("ix_tool_registry_name", "tool_registry", ["name"], unique=True)
    op.create_index("ix_tool_registry_type", "tool_registry", ["type"], unique=False)

    op.create_table(
        "model_deployments",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "router_config_id",
            GUID(),
            sa.ForeignKey("router_configs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("litellm_params", sa.JSON(), nullable=False),
        sa.Column("model_info", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_model_deployments_router",
        "model_deployments",
        ["router_config_id"],
        unique=False,
    )
    op.create_index("ix_model_deployments_model", "model_deployments", ["model_name"], unique=False)

    op.create_table(
        "agents",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "team_id",
            GUID(),
            sa.ForeignKey("teams.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("system_message", sa.Text(), nullable=True),
        sa.Column("instructions", sa.JSON(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=True),
        sa.Column("additional_context", sa.Text(), nullable=True),
        sa.Column("markdown", sa.Boolean(), nullable=False),
        sa.Column("add_datetime_to_context", sa.Boolean(), nullable=False),
        sa.Column("add_location_to_context", sa.Boolean(), nullable=False),
        sa.Column("enable_agentic_memory", sa.Boolean(), nullable=False),
        sa.Column("enable_user_memories", sa.Boolean(), nullable=False),
        sa.Column("enable_session_summaries", sa.Boolean(), nullable=False),
        sa.Column("add_history_to_context", sa.Boolean(), nullable=False),
        sa.Column("num_history_runs", sa.Integer(), nullable=False),
        sa.Column("tool_call_limit", sa.Integer(), nullable=True),
        sa.Column("output_schema", sa.String(length=255), nullable=True),
        sa.Column("structured_outputs", sa.Boolean(), nullable=False),
        sa.Column("reasoning", sa.Boolean(), nullable=False),
        sa.Column("reasoning_min_steps", sa.Integer(), nullable=False),
        sa.Column("reasoning_max_steps", sa.Integer(), nullable=False),
        sa.Column("model_config", sa.JSON(), nullable=False),
        sa.Column("reasoning_model_config", sa.JSON(), nullable=True),
        sa.Column("knowledge_config", sa.JSON(), nullable=True),
        sa.Column("tools", sa.JSON(), nullable=False),
        sa.Column("mcp_servers", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    op.create_index("ix_agents_name", "agents", ["name"], unique=False)
    op.create_index("ix_agents_team_id", "agents", ["team_id"], unique=False)

    op.create_table(
        "executions",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_type", execution_target_enum, nullable=False),
        sa.Column("target_id", GUID(), nullable=True),
        sa.Column(
            "agent_id",
            GUID(),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "team_id",
            GUID(),
            sa.ForeignKey("teams.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "workflow_id",
            GUID(),
            sa.ForeignKey("workflows.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "router_config_id",
            GUID(),
            sa.ForeignKey("router_configs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("session_id", sa.String(length=255), nullable=True),
        sa.Column("status", execution_status_enum, nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("output_payload", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("telemetry", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    op.create_index(
        "ix_executions_target",
        "executions",
        ["target_type", "target_id"],
        unique=False,
    )
    op.create_index("ix_executions_status", "executions", ["status"], unique=False)
    op.create_index("ix_executions_agent", "executions", ["agent_id"], unique=False)
    op.create_index("ix_executions_team", "executions", ["team_id"], unique=False)
    op.create_index("ix_executions_workflow", "executions", ["workflow_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_executions_workflow", table_name="executions")
    op.drop_index("ix_executions_team", table_name="executions")
    op.drop_index("ix_executions_agent", table_name="executions")
    op.drop_index("ix_executions_status", table_name="executions")
    op.drop_index("ix_executions_target", table_name="executions")
    op.drop_table("executions")

    op.drop_index("ix_agents_team_id", table_name="agents")
    op.drop_index("ix_agents_name", table_name="agents")
    op.drop_table("agents")

    op.drop_index("ix_model_deployments_model", table_name="model_deployments")
    op.drop_index("ix_model_deployments_router", table_name="model_deployments")
    op.drop_table("model_deployments")

    op.drop_index("ix_tool_registry_type", table_name="tool_registry")
    op.drop_index("ix_tool_registry_name", table_name="tool_registry")
    op.drop_table("tool_registry")

    op.drop_index("ix_workflows_name", table_name="workflows")
    op.drop_table("workflows")

    op.drop_index("ix_router_configs_name", table_name="router_configs")
    op.drop_table("router_configs")

    op.drop_index("ix_teams_name", table_name="teams")
    op.drop_table("teams")

    execution_status_enum.drop(op.get_bind(), checkfirst=True)
    execution_target_enum.drop(op.get_bind(), checkfirst=True)
