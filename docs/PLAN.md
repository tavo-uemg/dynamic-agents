# Dynamic Agents - Plano de Implementação Completo

## Visão Geral

Sistema para criação, persistência e execução dinâmica de agentes de IA usando **Agno** como framework de agentes e **LiteLLM Router** como camada de abstração de modelos.

**Repositório:** https://github.com/tavo-uemg/dynamic-agents

---

## Análise Detalhada das Tecnologias

### 1. Agno Framework (v2.4.4+)

#### 1.1 Agent Class - Parâmetros Principais

| Categoria | Parâmetros | Serializável |
|-----------|-----------|--------------|
| **Identificação** | `name`, `id`, `user_id`, `session_id` | ✅ |
| **Modelo** | `model`, `reasoning_model`, `parser_model`, `output_model` | ✅ (via to_dict) |
| **Instruções** | `system_message`, `instructions`, `description`, `expected_output`, `additional_context` | ✅ |
| **Contexto** | `markdown`, `add_datetime_to_context`, `add_location_to_context`, `add_name_to_context` | ✅ |
| **Memória** | `enable_agentic_memory`, `enable_user_memories`, `add_memories_to_context`, `enable_session_summaries` | ✅ |
| **Histórico** | `add_history_to_context`, `num_history_runs`, `num_history_messages` | ✅ |
| **Session State** | `session_state`, `add_session_state_to_context`, `enable_agentic_state` | ✅ |
| **Knowledge (RAG)** | `knowledge`, `add_knowledge_to_context`, `search_knowledge`, `knowledge_filters` | Parcial |
| **Tools** | `tools`, `tool_call_limit`, `show_tool_calls`, `read_chat_history`, `read_tool_call_history` | ✅ (via registry) |
| **Output** | `output_schema`, `parse_response`, `structured_outputs`, `use_json_mode` | ✅ (class name) |
| **Reasoning** | `reasoning`, `reasoning_min_steps`, `reasoning_max_steps` | ✅ |
| **Storage** | `db`, `store_media`, `store_tool_messages`, `store_history_messages` | ✅ |
| **Debug** | `debug_mode`, `show_tool_calls`, `telemetry` | ✅ |

#### 1.2 Team Class - Parâmetros Principais

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `members` | `List[Agent/Team]` | Agentes ou sub-teams membros |
| `model` | `Model/str` | Modelo do líder do team |
| `respond_directly` | `bool` | Se True, roteia diretamente para membro sem síntese |
| `delegate_to_all_members` | `bool` | Delega tarefa para todos os membros simultaneamente |
| `share_member_interactions` | `bool` | Membros veem interações uns dos outros |
| `add_team_history_to_members` | `bool` | Compartilha histórico do team com membros |
| `num_team_history_runs` | `int` | Número de runs anteriores a compartilhar |
| `get_member_information_tool` | `bool` | Adiciona tool para consultar informações dos membros |
| `store_member_responses` | `bool` | Persiste respostas individuais dos membros |

#### 1.3 Workflow Class - Parâmetros Principais

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `name` | `str` | Nome do workflow |
| `steps` | `List[Step/Parallel/Loop/Condition]` | Passos do workflow |
| `input_schema` | `BaseModel` | Schema de validação de entrada |
| `add_workflow_history_to_steps` | `bool` | Compartilha histórico com steps |
| `stream_executor_events` | `bool` | Streaming de eventos durante execução |
| `db` | `BaseDb` | Database para persistência |

#### 1.4 Tools & MCP

**Built-in Toolkits:**
- Search: `DuckDuckGoTools`, `GoogleSearchTools`, `ExaTools`, `ArxivTools`, `WikipediaTools`
- Finance: `YFinanceTools`, `OpenBBTools`
- Productivity: `GmailTools`, `GoogleCalendarTools`, `SlackTools`, `NotionTools`
- System: `ShellTools`, `PythonTools`, `FileTools`, `DockerTools`
- Data: `PostgresTools`, `SqlTools`, `PandasTools`
- AI/Media: `DalleTools`, `ElevenLabsTools`, `YoutubeTools`

**MCP Integration:**
```python
MCPTools(
    command="npx -y @mcp-server/...",  # Stdio connection
    url="https://...",                   # SSE/HTTP connection
    env={...},                           # Environment variables
    tool_name_prefix="..."               # Prefixo para evitar colisões
)
```

#### 1.5 Storage Adapters

| Tipo | Classes |
|------|---------|
| **SQL** | `PostgresDb`, `SqliteDb`, `MysqlDb`, `SingleStoreDb`, `SurrealDb` |
| **NoSQL** | `MongoDb`, `DynamoDb`, `FirestoreDb` |
| **Cache** | `RedisDb`, `InMemoryDb` |
| **Cloud** | `GcsJsonDb` |

#### 1.6 Knowledge & Vector DBs

**Vector DBs:**
- `PgVector`, `Pinecone`, `Qdrant`, `Milvus`, `Weaviate`, `Chroma`, `LanceDB`, `MongoDB`, `Redis`

**Embedders:**
- `OpenAIEmbedder`, `AzureOpenAIEmbedder`, `GeminiEmbedder`, `CohereEmbedder`, `OllamaEmbedder`, `HuggingFaceEmbedder`

**Readers:**
- `PDFReader`, `CSVReader`, `ExcelReader`, `DocxReader`, `JSONReader`, `MarkdownReader`, `YouTubeReader`

---

### 2. LiteLLM Router

#### 2.1 Router Class - Parâmetros

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `model_list` | `List[dict]` | Lista de deployments |
| `routing_strategy` | `str` | `simple-shuffle`, `least-busy`, `usage-based-routing`, `latency-based-routing`, `cost-based-routing` |
| `num_retries` | `int` | Número de retries |
| `timeout` | `float` | Timeout global |
| `fallbacks` | `List[dict]` | Mapeamento de fallbacks específicos |
| `default_fallbacks` | `List[str]` | Fallbacks globais |
| `context_window_fallbacks` | `List[dict]` | Fallbacks para erros de context window |
| `content_policy_fallbacks` | `List[dict]` | Fallbacks para violações de política |
| `allowed_fails` | `int` | Falhas antes de cooldown |
| `cooldown_time` | `float` | Tempo de cooldown em segundos |
| `enable_pre_call_checks` | `bool` | Verifica limits antes de chamar |
| `enable_tag_filtering` | `bool` | Habilita roteamento por tags |
| `cache_responses` | `bool` | Habilita caching |
| `redis_host/port/password` | `str` | Conexão Redis para load balancing |

#### 2.2 Model List Format

```python
{
    "model_name": "gpt-4-group",       # Nome abstrato
    "litellm_params": {
        "model": "azure/gpt-4-us-east", # Modelo real
        "api_key": "os.environ/KEY",    # Suporta env vars
        "api_base": "https://...",
        "rpm": 1000,                     # Rate limit: requests/min
        "tpm": 100000,                   # Rate limit: tokens/min
        "weight": 5,                     # Peso para routing
        "order": 1,                      # Prioridade (menor = maior)
        "tags": ["prod", "us"],          # Tags para filtering
        "max_parallel_requests": 10      # Limite de concorrência
    },
    "model_info": {
        "id": "deployment-1",
        "base_model": "gpt-4"
    }
}
```

#### 2.3 Providers Suportados (100+)

| Tier | Providers |
|------|-----------|
| **Tier 1** | OpenAI, Anthropic, Azure, Bedrock, Vertex AI, Gemini |
| **Open-Source** | Ollama, vLLM, Groq, Together, Fireworks, DeepInfra, OpenRouter |
| **Enterprise** | WatsonX, Sagemaker, Databricks, Cloudflare, Nvidia NIM |
| **Specialized** | Perplexity, Mistral, Cohere, DeepSeek, XAI (Grok) |

---

## Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                         REST API (FastAPI)                           │
├─────────────────────────────────────────────────────────────────────┤
│  POST /agents     POST /teams      POST /workflows    POST /execute  │
│  GET /agents/:id  GET /teams/:id   GET /workflows/:id  GET /runs/:id │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Core Management Layer                           │
├──────────────────┬──────────────────┬──────────────────────────────┤
│  AgentManager    │   TeamManager    │      WorkflowManager          │
│  - create()      │   - create()     │      - create()               │
│  - save()        │   - save()       │      - save()                 │
│  - load()        │   - load()       │      - load()                 │
│  - execute()     │   - execute()    │      - execute()              │
│  - delete()      │   - delete()     │      - delete()               │
└──────────────────┴──────────────────┴──────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌────────────────────────────┐      ┌────────────────────────────────┐
│     LiteLLM Router         │      │       Tool Registry             │
│  - model_list management   │      │  - Built-in tools               │
│  - fallback handling       │      │  - Custom functions             │
│  - tag-based routing       │      │  - MCP connections              │
│  - rate limiting           │      │  - Dynamic loading              │
└────────────────────────────┘      └────────────────────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Agno Framework                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │   Agent     │  │    Team     │  │  Workflow   │                  │
│  │ (Dynamic)   │  │ (Dynamic)   │  │ (Dynamic)   │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Storage Layer                                 │
├──────────────────┬──────────────────┬──────────────────────────────┤
│   PostgreSQL     │     Redis        │      Vector DB                │
│  - Agent configs │  - Session cache │  - Knowledge base             │
│  - Team configs  │  - Router state  │  - Embeddings                 │
│  - Workflows     │  - Rate limits   │  - Document chunks            │
│  - Executions    │                  │                               │
└──────────────────┴──────────────────┴──────────────────────────────┘
```

---

## Modelo de Dados

### Agent Configuration

```python
class AgentConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: Optional[str] = None
    version: int = 1
    
    # Model Configuration
    model_config: ModelConfig
    reasoning_model_config: Optional[ModelConfig] = None
    
    # Instructions
    system_message: Optional[str] = None
    instructions: List[str] = []
    expected_output: Optional[str] = None
    additional_context: Optional[str] = None
    
    # Context Settings
    markdown: bool = False
    add_datetime_to_context: bool = False
    add_location_to_context: bool = False
    
    # Memory Settings
    enable_agentic_memory: bool = False
    enable_user_memories: bool = False
    enable_session_summaries: bool = False
    add_history_to_context: bool = True
    num_history_runs: int = 3
    
    # Tools Configuration
    tools: List[ToolConfig] = []
    mcp_servers: List[MCPServerConfig] = []
    tool_call_limit: Optional[int] = None
    
    # Output Configuration
    output_schema: Optional[str] = None  # Nome da classe Pydantic
    structured_outputs: bool = False
    
    # Reasoning
    reasoning: bool = False
    reasoning_min_steps: int = 1
    reasoning_max_steps: int = 10
    
    # Knowledge
    knowledge_config: Optional[KnowledgeConfig] = None
    
    # Metadata
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
```

### Team Configuration

```python
class TeamConfig(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    
    # Model for leader
    model_config: ModelConfig
    
    # Members (can be agent IDs or nested team IDs)
    member_ids: List[str] = []
    
    # Coordination
    respond_directly: bool = False
    delegate_to_all_members: bool = False
    share_member_interactions: bool = False
    add_team_history_to_members: bool = False
    num_team_history_runs: int = 3
    
    # Instructions
    instructions: List[str] = []
    
    # Metadata
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime
```

### Workflow Configuration

```python
class WorkflowConfig(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    
    # Steps
    steps: List[StepConfig] = []
    
    # Input validation
    input_schema: Optional[str] = None
    
    # Settings
    add_workflow_history_to_steps: bool = False
    stream_executor_events: bool = True
    
    # Metadata
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime

class StepConfig(BaseModel):
    name: str
    type: Literal["agent", "team", "parallel", "condition", "loop"]
    executor_id: Optional[str] = None  # Agent or Team ID
    parallel_steps: Optional[List["StepConfig"]] = None
    condition: Optional[str] = None
    loop_condition: Optional[str] = None
```

### Model Configuration (LiteLLM)

```python
class ModelConfig(BaseModel):
    # Router group name
    model_name: str
    
    # Optional specific deployment
    deployment_id: Optional[str] = None
    
    # Request-level overrides
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    
    # Routing tags
    tags: List[str] = []

class RouterConfig(BaseModel):
    # Model deployments
    model_list: List[ModelDeployment] = []
    
    # Routing strategy
    routing_strategy: str = "simple-shuffle"
    
    # Reliability
    num_retries: int = 3
    timeout: float = 60.0
    allowed_fails: int = 3
    cooldown_time: float = 30.0
    
    # Fallbacks
    fallbacks: Dict[str, List[str]] = {}
    default_fallbacks: List[str] = []
    context_window_fallbacks: Dict[str, List[str]] = {}
    
    # Features
    enable_pre_call_checks: bool = True
    enable_tag_filtering: bool = True
    cache_responses: bool = True
    
    # Redis (for distributed)
    redis_host: Optional[str] = None
    redis_port: Optional[int] = None
    redis_password: Optional[str] = None

class ModelDeployment(BaseModel):
    model_name: str
    litellm_params: Dict[str, Any]
    model_info: Optional[Dict[str, Any]] = None
```

### Tool Configuration

```python
class ToolConfig(BaseModel):
    type: Literal["builtin", "function", "mcp"]
    
    # For builtin tools
    toolkit_name: Optional[str] = None
    toolkit_params: Dict[str, Any] = {}
    
    # For custom functions
    function_name: Optional[str] = None
    function_module: Optional[str] = None
    
    # For MCP
    mcp_server: Optional[MCPServerConfig] = None

class MCPServerConfig(BaseModel):
    connection_type: Literal["command", "url"]
    command: Optional[str] = None
    url: Optional[str] = None
    env: Dict[str, str] = {}
    tool_name_prefix: Optional[str] = None
```

---

## Plano de Implementação por Fases

### Fase 1: Core Infrastructure (Semana 1)

#### 1.1 Database Models (SQLAlchemy)
- [ ] `agents` table - configurações de agentes
- [ ] `teams` table - configurações de teams
- [ ] `workflows` table - configurações de workflows
- [ ] `model_deployments` table - deployments do LiteLLM
- [ ] `router_configs` table - configurações do router
- [ ] `tool_registry` table - registro de tools customizadas
- [ ] `executions` table - histórico de execuções
- [ ] Migrations com Alembic

#### 1.2 Pydantic Schemas
- [ ] AgentConfig, AgentCreate, AgentUpdate
- [ ] TeamConfig, TeamCreate, TeamUpdate
- [ ] WorkflowConfig, WorkflowCreate, WorkflowUpdate
- [ ] ModelConfig, RouterConfig, ModelDeployment
- [ ] ToolConfig, MCPServerConfig
- [ ] ExecutionResult, RunOutput

#### 1.3 LiteLLM Router Manager
- [ ] RouterManager class
- [ ] CRUD para model_list
- [ ] Hot-reload de configurações
- [ ] Fallback configuration
- [ ] Tag-based routing setup
- [ ] Rate limiting integration
- [ ] Redis connection management

### Fase 2: Agent Management (Semana 2)

#### 2.1 Agent Factory
- [ ] `AgentFactory.create_from_config(config: AgentConfig) -> Agent`
- [ ] Model instantiation via LiteLLM
- [ ] Tool attachment (builtin + custom)
- [ ] MCP connection management
- [ ] Knowledge base attachment
- [ ] Output schema resolution

#### 2.2 Agent Repository
- [ ] `AgentRepository.save(agent: Agent) -> str`
- [ ] `AgentRepository.load(agent_id: str) -> Agent`
- [ ] `AgentRepository.list(filters) -> List[AgentConfig]`
- [ ] `AgentRepository.delete(agent_id: str)`
- [ ] Version management
- [ ] Config diff/merge

#### 2.3 Agent Serialization
- [ ] `agent_to_config(agent: Agent) -> AgentConfig`
- [ ] `config_to_agent(config: AgentConfig) -> Agent`
- [ ] Tool registry for function rehydration
- [ ] Schema registry for output models

### Fase 3: Team & Workflow Management (Semana 3)

#### 3.1 Team Factory
- [ ] `TeamFactory.create_from_config(config: TeamConfig) -> Team`
- [ ] Member resolution (load agents/sub-teams)
- [ ] Coordination mode setup
- [ ] Shared context configuration

#### 3.2 Workflow Factory
- [ ] `WorkflowFactory.create_from_config(config: WorkflowConfig) -> Workflow`
- [ ] Step resolution
- [ ] Parallel step handling
- [ ] Condition/Loop parsing

#### 3.3 Execution Engine
- [ ] `ExecutionEngine.run_agent(agent_id, input, session_id)`
- [ ] `ExecutionEngine.run_team(team_id, input, session_id)`
- [ ] `ExecutionEngine.run_workflow(workflow_id, input)`
- [ ] Streaming support
- [ ] Event collection
- [ ] Result persistence

### Fase 4: Tool System (Semana 4)

#### 4.1 Tool Registry
- [ ] Built-in tool catalog
- [ ] Custom function registration
- [ ] Function serialization/deserialization
- [ ] Dynamic import from modules

#### 4.2 MCP Manager
- [ ] MCP connection pool
- [ ] Server lifecycle management
- [ ] Tool discovery and registration
- [ ] Connection health monitoring

#### 4.3 Tool Execution
- [ ] Execution context injection
- [ ] Result caching
- [ ] Error handling and retries
- [ ] Audit logging

### Fase 5: Knowledge System (Semana 5)

#### 5.1 Knowledge Manager
- [ ] Knowledge configuration persistence
- [ ] Vector DB connection management
- [ ] Embedder configuration
- [ ] Content ingestion pipeline

#### 5.2 RAG Integration
- [ ] Automatic context injection
- [ ] Search tool generation
- [ ] Retrieval filtering
- [ ] Reranking support

### Fase 6: REST API (Semana 6)

#### 6.1 Agent Endpoints
- [ ] `POST /api/v1/agents` - Create agent
- [ ] `GET /api/v1/agents` - List agents
- [ ] `GET /api/v1/agents/{id}` - Get agent
- [ ] `PUT /api/v1/agents/{id}` - Update agent
- [ ] `DELETE /api/v1/agents/{id}` - Delete agent
- [ ] `POST /api/v1/agents/{id}/execute` - Execute agent

#### 6.2 Team Endpoints
- [ ] `POST /api/v1/teams` - Create team
- [ ] `GET /api/v1/teams` - List teams
- [ ] `GET /api/v1/teams/{id}` - Get team
- [ ] `PUT /api/v1/teams/{id}` - Update team
- [ ] `DELETE /api/v1/teams/{id}` - Delete team
- [ ] `POST /api/v1/teams/{id}/execute` - Execute team

#### 6.3 Workflow Endpoints
- [ ] `POST /api/v1/workflows` - Create workflow
- [ ] `GET /api/v1/workflows` - List workflows
- [ ] `GET /api/v1/workflows/{id}` - Get workflow
- [ ] `PUT /api/v1/workflows/{id}` - Update workflow
- [ ] `DELETE /api/v1/workflows/{id}` - Delete workflow
- [ ] `POST /api/v1/workflows/{id}/execute` - Execute workflow

#### 6.4 Router Endpoints
- [ ] `GET /api/v1/router/config` - Get router config
- [ ] `PUT /api/v1/router/config` - Update router config
- [ ] `POST /api/v1/router/deployments` - Add deployment
- [ ] `DELETE /api/v1/router/deployments/{id}` - Remove deployment
- [ ] `GET /api/v1/router/health` - Router health check

#### 6.5 Tool Endpoints
- [ ] `GET /api/v1/tools` - List available tools
- [ ] `POST /api/v1/tools/custom` - Register custom tool
- [ ] `GET /api/v1/tools/mcp` - List MCP servers
- [ ] `POST /api/v1/tools/mcp` - Register MCP server

#### 6.6 Execution Endpoints
- [ ] `GET /api/v1/executions` - List executions
- [ ] `GET /api/v1/executions/{id}` - Get execution details
- [ ] `GET /api/v1/executions/{id}/stream` - Stream execution (SSE)

### Fase 7: CLI & Polish (Semana 7)

#### 7.1 CLI Commands (Typer)
- [ ] `dynamic-agents serve` - Start API server
- [ ] `dynamic-agents agent create/list/delete`
- [ ] `dynamic-agents team create/list/delete`
- [ ] `dynamic-agents workflow create/list/delete`
- [ ] `dynamic-agents execute agent/team/workflow`
- [ ] `dynamic-agents router config/status`

#### 7.2 Documentation
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Usage examples
- [ ] Configuration reference

#### 7.3 Testing
- [ ] Unit tests for all managers
- [ ] Integration tests for API
- [ ] E2E tests with real models

---

## Exemplos de Uso

### Criar Agent via API

```json
POST /api/v1/agents
{
  "name": "Research Assistant",
  "description": "Agent for research tasks",
  "model_config": {
    "model_name": "gpt-4-group",
    "temperature": 0.7
  },
  "instructions": [
    "You are a helpful research assistant",
    "Always cite your sources",
    "Be concise but thorough"
  ],
  "tools": [
    {"type": "builtin", "toolkit_name": "DuckDuckGoTools"},
    {"type": "builtin", "toolkit_name": "WikipediaTools"}
  ],
  "enable_agentic_memory": true,
  "add_history_to_context": true,
  "tags": ["research", "production"]
}
```

### Criar Team via API

```json
POST /api/v1/teams
{
  "name": "Content Team",
  "description": "Team for content creation",
  "model_config": {
    "model_name": "gpt-4-group"
  },
  "member_ids": ["agent-researcher-id", "agent-writer-id"],
  "respond_directly": false,
  "share_member_interactions": true,
  "instructions": ["Coordinate to produce high-quality content"]
}
```

### Configurar Router via API

```json
PUT /api/v1/router/config
{
  "model_list": [
    {
      "model_name": "gpt-4-group",
      "litellm_params": {
        "model": "azure/gpt-4-east",
        "api_key": "os.environ/AZURE_API_KEY",
        "api_base": "https://my-endpoint.openai.azure.com/",
        "rpm": 500,
        "tags": ["prod", "us-east"]
      }
    },
    {
      "model_name": "gpt-4-group",
      "litellm_params": {
        "model": "openai/gpt-4o",
        "api_key": "os.environ/OPENAI_API_KEY",
        "rpm": 1000,
        "tags": ["prod", "openai"]
      }
    },
    {
      "model_name": "fast-model",
      "litellm_params": {
        "model": "groq/llama3-70b-8192",
        "api_key": "os.environ/GROQ_API_KEY"
      }
    }
  ],
  "routing_strategy": "usage-based-routing",
  "fallbacks": {"gpt-4-group": ["fast-model"]},
  "enable_tag_filtering": true,
  "enable_pre_call_checks": true
}
```

### Executar Agent

```json
POST /api/v1/agents/{agent_id}/execute
{
  "input": "Research the latest developments in quantum computing",
  "session_id": "user-123-session",
  "stream": true
}
```

---

## Considerações Técnicas

### Serialização de Funções

Para serializar funções customizadas:

1. **Registry Pattern**: Manter um registro global de funções por nome
2. **Module + Name**: Salvar `module.path:function_name` e importar dinamicamente
3. **Code Storage**: Para casos extremos, salvar o código-fonte (com cuidado de segurança)

### MCP Connection Management

1. Conexões MCP são stateful
2. Usar connection pool por servidor
3. Implementar health checks
4. Reconexão automática com backoff

### LiteLLM Router Hot-Reload

1. Router suporta `set_model_list()` para atualização dinâmica
2. Usar Redis para estado compartilhado entre instâncias
3. Implementar webhook para notificação de mudanças

### Segurança

1. Nunca salvar API keys diretamente - usar `os.environ/KEY_NAME`
2. Validar input schemas
3. Rate limiting por usuário/API key
4. Audit logging de todas as execuções
5. Sandbox para execução de código (ShellTools, PythonTools)

---

## Próximos Passos Imediatos

1. **Implementar database models** (SQLAlchemy + Alembic)
2. **Criar LiteLLM Router Manager** com suporte a hot-reload
3. **Implementar Agent Factory** com todos os parâmetros mapeados
4. **Criar Tool Registry** com suporte a builtin + custom + MCP
5. **Desenvolver API REST** com FastAPI

---

## Dependências Finais

```toml
[project.dependencies]
agno = ">=1.0.0"
litellm = ">=1.50.0"
sqlalchemy = ">=2.0.0"
alembic = ">=1.13.0"
pydantic = ">=2.0.0"
pydantic-settings = ">=2.0.0"
python-dotenv = ">=1.0.0"
fastapi = ">=0.115.0"
uvicorn = ">=0.30.0"
aiosqlite = ">=0.20.0"
asyncpg = ">=0.29.0"
redis = ">=5.0.0"
httpx = ">=0.27.0"
rich = ">=13.0.0"
typer = ">=0.12.0"
```
