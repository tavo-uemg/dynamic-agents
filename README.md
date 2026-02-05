# Dynamic Agents

Dynamic AI Agent creation, persistence and execution with Agno and LiteLLM Router.

## Features

- **Dynamic Agent Creation**: Create AI agents programmatically with full customization
- **Persistence**: Save and restore agents, teams, and workflows to/from database
- **LiteLLM Router Integration**: Multi-model support with fallback, load balancing, and tag-based routing
- **Team & Workflow Support**: Create agent teams and complex workflows
- **Tool Integration**: Dynamic tool attachment and MCP (Model Context Protocol) support
- **API & CLI**: Full REST API and command-line interface

## Installation

```bash
pip install dynamic-agents
```

## Quick Start

```python
from dynamic_agents import DynamicAgentManager

# Initialize manager with LiteLLM Router
manager = DynamicAgentManager()

# Create an agent dynamically
agent_config = {
    "name": "researcher",
    "description": "Research assistant",
    "model": "gpt-4o",
    "tools": ["web_search", "file_reader"],
    "instructions": "You are a helpful research assistant."
}

agent = manager.create_agent(agent_config)

# Save to database
agent_id = manager.save_agent(agent)

# Restore and execute
restored_agent = manager.load_agent(agent_id)
response = await restored_agent.run("What is quantum computing?")
```

## Architecture

```
dynamic_agents/
├── core/           # Core agent management
├── models/         # Database models
├── storage/        # Persistence layer
├── router/         # LiteLLM Router integration
├── tools/          # Tool management
├── mcp/            # MCP integration
└── api/            # REST API
```

## License

MIT
