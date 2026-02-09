"""Initial database schema covering agents, teams, workflows and executions."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from dynamic_agents.models import (
    AgentStatus,
    ExecutionStatus,
    ExecutionTargetType,
    GUID,
    JSONBType,
    MCPConnectionType,
    ModelDeploymentStatus,
    RouterStatus,
    RoutingStrategy,
    TeamStatus,
    ToolStatus,
    ToolType,
    WorkflowStatus,
)


revision = "202402050001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:  # noqa: D103
    op.create_table(
        "agents",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", GUID(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "status",
            sa.Enum(AgentStatus, name="agent_status"),
            nullable=False,
        ),
        sa.Column("system_message", sa.Text(), nullable=True),
        sa.Column("instructions", JSONBType(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("expected_output", sa.Text(), nullable=True),
        sa.Column("additional_context", sa.Text(), nullable=True),
        sa.Column("markdown", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "add_datetime_to_context", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "add_location_to_context", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("add_name_to_context", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "enable_agentic_memory", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "enable_user_memories", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "enable_session_summaries", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "add_history_to_context", sa.Boolean(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("num_history_runs", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column(
            "num_history_messages", sa.Integer(), nullable=False, server_default=sa.text("20")
        ),
        sa.Column("tool_call_limit", sa.Integer(), nullable=True),
        sa.Column("show_tool_calls", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("read_chat_history", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "read_tool_call_history", sa.Boolean(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("output_schema", sa.String(length=255), nullable=True),
        sa.Column("structured_outputs", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("parse_response", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("use_json_mode", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("reasoning", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("reasoning_min_steps", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "reasoning_max_steps", sa.Integer(), nullable=False, server_default=sa.text("10")
        ),
        sa.Column("model_config", JSONBType(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("reasoning_model_config", JSONBType(), nullable=True),
        sa.Column("knowledge_config", JSONBType(), nullable=True),
        sa.Column("tools", JSONBType(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("mcp_servers", JSONBType(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("tags", JSONBType(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata", JSONBType(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_agents_name", "agents", ["name"], unique=False)
    op.create_index("ix_agents_user_id", "agents", ["user_id"], unique=False)
    op.create_index("ix_agents_tags", "agents", ["tags"], unique=False)

    op.create_table(
        "teams",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", GUID(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(TeamStatus, name="team_status"),
            nullable=False,
        ),
        sa.Column("model_config", JSONBType(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("member_ids", JSONBType(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("instructions", JSONBType(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("respond_directly", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "delegate_to_all_members", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "share_member_interactions", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "add_team_history_to_members", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "num_team_history_runs", sa.Integer(), nullable=False, server_default=sa.text("3")
        ),
        sa.Column(
            "get_member_information_tool", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "store_member_responses", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("tags", JSONBType(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata", JSONBType(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_teams_name", "teams", ["name"], unique=False)
    op.create_index("ix_teams_user_id", "teams", ["user_id"], unique=False)
    op.create_index("ix_teams_tags", "teams", ["tags"], unique=False)

    op.create_table(
        "workflows",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", GUID(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(WorkflowStatus, name="workflow_status"),
            nullable=False,
        ),
        sa.Column("steps", JSONBType(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("input_schema", sa.Text(), nullable=True),
        sa.Column(
            "add_workflow_history_to_steps",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "stream_executor_events", sa.Boolean(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("tags", JSONBType(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata", JSONBType(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_workflows_name", "workflows", ["name"], unique=False)
    op.create_index("ix_workflows_user_id", "workflows", ["user_id"], unique=False)
    op.create_index("ix_workflows_tags", "workflows", ["tags"], unique=False)

    op.create_table(
        "router_configs",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", GUID(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(RouterStatus, name="router_status"),
            nullable=False,
        ),
        sa.Column(
            "routing_strategy",
            sa.Enum(RoutingStrategy, name="routing_strategy"),
            nullable=False,
        ),
        sa.Column("num_retries", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("timeout", sa.Float(), nullable=False, server_default=sa.text("60")),
        sa.Column("allowed_fails", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("cooldown_time", sa.Float(), nullable=False, server_default=sa.text("30")),
        sa.Column("fallbacks", JSONBType(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("default_fallbacks", JSONBType(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "context_window_fallbacks", JSONBType(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column(
            "content_policy_fallbacks", JSONBType(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column(
            "enable_pre_call_checks", sa.Boolean(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column(
            "enable_tag_filtering", sa.Boolean(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("cache_responses", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("enable_rate_limits", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("redis_host", sa.String(length=255), nullable=True),
        sa.Column("redis_port", sa.Integer(), nullable=True),
        sa.Column("redis_password", sa.String(length=255), nullable=True),
        sa.Column("tags", JSONBType(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata", JSONBType(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_router_configs_name", "router_configs", ["name"], unique=False)
    op.create_index("ix_router_configs_user_id", "router_configs", ["user_id"], unique=False)
    op.create_index("ix_router_configs_tags", "router_configs", ["tags"], unique=False)

    op.create_table(
        "model_deployments",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "router_config_id",
            GUID(),
            sa.ForeignKey("router_configs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(ModelDeploymentStatus, name="model_deployment_status"),
            nullable=False,
        ),
        sa.Column("litellm_params", JSONBType(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("model_info", JSONBType(), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("tags", JSONBType(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.create_index(
        "ix_model_deployments_router",
        "model_deployments",
        ["router_config_id"],
        unique=False,
    )
    op.create_index(
        "ix_model_deployments_model",
        "model_deployments",
        ["model_name"],
        unique=False,
    )

    op.create_table(
        "tools",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", GUID(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "type",
            sa.Enum(ToolType, name="tool_type"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(ToolStatus, name="tool_status"),
            nullable=False,
        ),
        sa.Column("toolkit_name", sa.String(length=255), nullable=True),
        sa.Column("toolkit_params", JSONBType(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("function_name", sa.String(length=255), nullable=True),
        sa.Column("function_module", sa.String(length=255), nullable=True),
        sa.Column("function_path", sa.String(length=512), nullable=True),
        sa.Column("function_kwargs", JSONBType(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("timeout_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "mcp_connection_type",
            sa.Enum(MCPConnectionType, name="mcp_connection_type"),
            nullable=True,
        ),
        sa.Column("mcp_command", sa.String(length=512), nullable=True),
        sa.Column("mcp_url", sa.String(length=512), nullable=True),
        sa.Column("mcp_env", JSONBType(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("mcp_tool_name_prefix", sa.String(length=255), nullable=True),
        sa.Column("tags", JSONBType(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata", JSONBType(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.create_index("ix_tools_name", "tools", ["name"], unique=False)
    op.create_index("ix_tools_user_id", "tools", ["user_id"], unique=False)
    op.create_index("ix_tools_tags", "tools", ["tags"], unique=False)

    op.create_table(
        "executions",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", GUID(), nullable=True),
        sa.Column(
            "target_type",
            sa.Enum(ExecutionTargetType, name="execution_target_type"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(ExecutionStatus, name="execution_status"),
            nullable=False,
        ),
        sa.Column("agent_id", GUID(), sa.ForeignKey("agents.id", ondelete="SET NULL")),
        sa.Column("team_id", GUID(), sa.ForeignKey("teams.id", ondelete="SET NULL")),
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
        sa.Column("request_id", sa.String(length=255), nullable=True),
        sa.Column("input_payload", JSONBType(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("output_payload", JSONBType(), nullable=True),
        sa.Column("tool_calls", JSONBType(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("run_metadata", JSONBType(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_executions_status", "executions", ["status"], unique=False)
    op.create_index("ix_executions_agent_id", "executions", ["agent_id"], unique=False)
    op.create_index("ix_executions_team_id", "executions", ["team_id"], unique=False)
    op.create_index("ix_executions_workflow_id", "executions", ["workflow_id"], unique=False)
    op.create_index("ix_executions_user_id", "executions", ["user_id"], unique=False)


def downgrade() -> None:  # noqa: D103
    op.drop_index("ix_executions_user_id", table_name="executions")
    op.drop_index("ix_executions_workflow_id", table_name="executions")
    op.drop_index("ix_executions_team_id", table_name="executions")
    op.drop_index("ix_executions_agent_id", table_name="executions")
    op.drop_index("ix_executions_status", table_name="executions")
    op.drop_table("executions")

    op.drop_index("ix_tools_tags", table_name="tools")
    op.drop_index("ix_tools_user_id", table_name="tools")
    op.drop_index("ix_tools_name", table_name="tools")
    op.drop_table("tools")

    op.drop_index("ix_model_deployments_model", table_name="model_deployments")
    op.drop_index("ix_model_deployments_router", table_name="model_deployments")
    op.drop_table("model_deployments")

    op.drop_index("ix_router_configs_tags", table_name="router_configs")
    op.drop_index("ix_router_configs_user_id", table_name="router_configs")
    op.drop_index("ix_router_configs_name", table_name="router_configs")
    op.drop_table("router_configs")

    op.drop_index("ix_workflows_tags", table_name="workflows")
    op.drop_index("ix_workflows_user_id", table_name="workflows")
    op.drop_index("ix_workflows_name", table_name="workflows")
    op.drop_table("workflows")

    op.drop_index("ix_teams_tags", table_name="teams")
    op.drop_index("ix_teams_user_id", table_name="teams")
    op.drop_index("ix_teams_name", table_name="teams")
    op.drop_table("teams")

    op.drop_index("ix_agents_tags", table_name="agents")
    op.drop_index("ix_agents_user_id", table_name="agents")
    op.drop_index("ix_agents_name", table_name="agents")
    op.drop_table("agents")
