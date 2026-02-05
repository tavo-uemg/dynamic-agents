# Plano de Integração: Dynamic Agents + Agno Interfaces + A8N Identity (Secrets)

## Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CLIENTS / INTERFACES                                │
│                                                                                  │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│   │   Discord   │    │    Slack    │    │   WhatsApp  │    │   REST API  │      │
│   │  Interface  │    │  Interface  │    │  Interface  │    │   Client    │      │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘      │
│          │                  │                  │                  │              │
│          └────────────────┬─┴──────────────────┴─────────────────┘              │
│                           │                                                      │
│                           ▼                                                      │
│   ┌───────────────────────────────────────────────────────────────┐             │
│   │                    agno-interfaces                             │             │
│   │  (FastStream - Redis Streams | Discord Gateway | REST)         │             │
│   │                                                                │             │
│   │  Responsabilidades:                                            │             │
│   │  - Receber eventos de plataformas externas                     │             │
│   │  - Normalizar eventos em formato padrão                        │             │
│   │  - Publicar eventos no Message Broker                          │             │
│   │  - Entregar respostas para as plataformas                      │             │
│   └───────────────────────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Redis Streams / gRPC / HTTP
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           MESSAGE BROKER (Redis Streams)                         │
│                                                                                  │
│   Streams:                                                                       │
│   ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                    │
│   │ agent:requests │  │ agent:responses│  │ agent:events   │                    │
│   └────────────────┘  └────────────────┘  └────────────────┘                    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            dynamic-agents                                        │
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                           Event Router                                   │   │
│   │  - Recebe eventos do Message Broker                                      │   │
│   │  - Resolve qual Agent/Team/Workflow executar                             │   │
│   │  - Gerencia execução e respostas                                         │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                             │
│            ┌───────────────────────┼───────────────────────┐                    │
│            ▼                       ▼                       ▼                    │
│   ┌────────────────┐      ┌────────────────┐      ┌────────────────┐           │
│   │ Agent Manager  │      │  Team Manager  │      │Workflow Manager│           │
│   │                │      │                │      │                │           │
│   │ - Create/Load  │      │ - Create/Load  │      │ - Create/Load  │           │
│   │ - Execute      │      │ - Coordinate   │      │ - Execute Steps│           │
│   │ - Persist      │      │ - Persist      │      │ - Persist      │           │
│   └────────────────┘      └────────────────┘      └────────────────┘           │
│            │                       │                       │                    │
│            └───────────────────────┼───────────────────────┘                    │
│                                    ▼                                             │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                        LiteLLM Router                                    │   │
│   │  - Multi-provider support (100+ models)                                  │   │
│   │  - Fallback, Load Balancing, Rate Limiting                               │   │
│   │  - Tag-based routing                                                     │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                             │
│                                    ▼                                             │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                     Secrets Integration (A8N)                            │   │
│   │  - Busca API keys e tokens do Identity Service                           │   │
│   │  - Cache local com TTL                                                   │   │
│   │  - Refresh automático                                                    │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        A8N Identity Service (Port 8000)                          │
│                                                                                  │
│   Endpoints relevantes:                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ POST   /api/v1/secrets           - Criar secret                         │   │
│   │ GET    /api/v1/secrets           - Listar secrets do usuário            │   │
│   │ GET    /api/v1/secrets/{id}      - Buscar secret                         │   │
│   │ GET    /api/v1/secrets/{id}/values - Buscar valores decriptados         │   │
│   │ PATCH  /api/v1/secrets/{id}      - Atualizar secret                      │   │
│   │ DELETE /api/v1/secrets/{id}      - Deletar secret                        │   │
│   │                                                                          │   │
│   │ GET    /api/v1/providers         - Listar providers disponíveis          │   │
│   │ GET    /api/v1/providers/{name}/schema - Schema de um provider          │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│   Secrets armazenados:                                                           │
│   - openai (api_key, org_id)                                                    │
│   - anthropic (api_key)                                                         │
│   - azure_openai (api_key, endpoint, api_version)                               │
│   - discord (bot_token, application_id)                                         │
│   - groq (api_key)                                                              │
│   - ...                                                                          │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Opções de Comunicação entre Componentes

### Opção 1: Redis Streams (RECOMENDADO ✅)

**Por que é a melhor opção:**

1. **Já usado no agno-interfaces** - FastStreamInterface já implementa Redis Streams
2. **Desacoplamento total** - Interfaces não precisam conhecer dynamic-agents diretamente
3. **Escalabilidade** - Múltiplos workers podem consumir do mesmo stream
4. **Persistência** - Mensagens não se perdem se o consumer estiver offline
5. **Ordering garantido** - Mensagens processadas na ordem correta
6. **Consumer Groups** - Permite múltiplos consumidores com acknowledgment

```python
# agno-interfaces publica evento
await publisher.publish({
    "type": "discord.message",
    "source": "discord",
    "channel_id": "123456789",
    "guild_id": "987654321",
    "user_id": "111222333",
    "content": "Hello agent!",
    "metadata": {
        "agent_id": "research-agent",  # Qual agente deve processar
        "session_id": "discord:123456789",
        "reply_to": "agent:responses:discord:123456789"
    }
})

# dynamic-agents consome e processa
async def handle_agent_request(event: AgentRequestEvent):
    agent = await agent_manager.load(event.metadata.agent_id)
    response = await agent.arun(
        event.content,
        session_id=event.metadata.session_id
    )
    await publisher.publish(
        stream=event.metadata.reply_to,
        message={"content": response.content, "event_id": event.id}
    )
```

**Fluxo completo:**
```
Discord → DiscordInterface → Redis[agent:requests] → dynamic-agents → 
Agent.arun() → Redis[agent:responses:discord:channel_id] → DiscordInterface → Discord
```

---

### Opção 2: gRPC (Alta Performance)

**Quando usar:**
- Latência crítica (< 10ms)
- Comunicação síncrona necessária
- Streaming bidirecional

```protobuf
service DynamicAgentService {
    rpc Execute(ExecuteRequest) returns (ExecuteResponse);
    rpc ExecuteStream(ExecuteRequest) returns (stream ExecuteEvent);
    rpc GetAgent(GetAgentRequest) returns (AgentConfig);
    rpc CreateAgent(CreateAgentRequest) returns (AgentConfig);
}

message ExecuteRequest {
    string agent_id = 1;
    string input = 2;
    string session_id = 3;
    map<string, string> metadata = 4;
}
```

**Prós:**
- Muito rápido (HTTP/2 + Protobuf)
- Type-safe com código gerado
- Streaming nativo

**Contras:**
- Acoplamento mais forte
- Precisa do servidor online
- Mais complexo de implementar

---

### Opção 3: HTTP/REST (Simplicidade)

**Quando usar:**
- Integração simples
- Debugging fácil
- Clients diversos

```python
# agno-interfaces chama dynamic-agents via HTTP
async def call_agent(agent_id: str, input: str, session_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{DYNAMIC_AGENTS_URL}/api/v1/agents/{agent_id}/execute",
            json={
                "input": input,
                "session_id": session_id,
                "stream": False
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

**Prós:**
- Simples de implementar
- Fácil de debugar
- Swagger/OpenAPI

**Contras:**
- Síncrono (pode bloquear)
- Sem persistência de mensagens
- Menos escalável

---

## Recomendação: Arquitetura Híbrida

```
┌─────────────────────────────────────────────────────────────────┐
│                     PADRÃO RECOMENDADO                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. EVENTOS ASSÍNCRONOS (Redis Streams)                         │
│     - Discord messages → agent:requests                         │
│     - Slack events → agent:requests                             │
│     - Webhooks → agent:requests                                 │
│                                                                 │
│  2. API REST (dynamic-agents)                                   │
│     - CRUD de agents/teams/workflows                            │
│     - Configuração do router                                    │
│     - Dashboard/Admin                                           │
│                                                                 │
│  3. SECRETS (A8N Identity via REST)                             │
│     - Busca secrets sob demanda                                 │
│     - Cache local com TTL                                       │
│     - Refresh em background                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Integração com A8N Secrets

### Fluxo de Secrets

```
┌─────────────────────────────────────────────────────────────────┐
│                    SECRETS FLOW                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. STARTUP                                                     │
│     dynamic-agents inicia                                       │
│     → Autentica com A8N Identity (JWT)                          │
│     → Carrega lista de secrets disponíveis                      │
│     → Cache inicial dos secrets necessários                     │
│                                                                 │
│  2. AGENT EXECUTION                                             │
│     Agent precisa de api_key para "openai"                      │
│     → SecretsManager.get("openai", "api_key")                   │
│     → Verifica cache local                                      │
│     → Se expirado: GET /api/v1/secrets/{id}/values              │
│     → Decripta e retorna                                        │
│                                                                 │
│  3. LITELLM ROUTER                                              │
│     Router precisa configurar deployments                       │
│     → Para cada deployment no model_list:                       │
│       - Resolve "os.environ/OPENAI_API_KEY"                     │
│       - SecretsManager.get("openai", "api_key")                 │
│       - Injeta no litellm_params                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Implementação do SecretsManager

```python
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import httpx
from pydantic import BaseModel
from cachetools import TTLCache

class SecretValue(BaseModel):
    value: str
    expires_at: datetime
    
class SecretsManager:
    def __init__(
        self,
        identity_url: str,
        service_token: str,
        cache_ttl: int = 300,  # 5 minutos
        max_cache_size: int = 100
    ):
        self.identity_url = identity_url
        self.service_token = service_token
        self._cache: TTLCache = TTLCache(maxsize=max_cache_size, ttl=cache_ttl)
        self._client: Optional[httpx.AsyncClient] = None
    
    async def get_secret(
        self, 
        provider: str, 
        field: str,
        user_id: Optional[str] = None
    ) -> Optional[str]:
        cache_key = f"{user_id or 'system'}:{provider}:{field}"
        
        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Fetch from A8N Identity
        secret = await self._fetch_secret(provider, field, user_id)
        if secret:
            self._cache[cache_key] = secret
        
        return secret
    
    async def _fetch_secret(
        self, 
        provider: str, 
        field: str,
        user_id: Optional[str] = None
    ) -> Optional[str]:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.identity_url,
                headers={"Authorization": f"Bearer {self.service_token}"}
            )
        
        # List secrets by provider
        params = {"provider": provider}
        if user_id:
            params["user_id"] = user_id
            
        response = await self._client.get("/api/v1/secrets", params=params)
        if response.status_code != 200:
            return None
        
        secrets = response.json()["items"]
        if not secrets:
            return None
        
        # Get secret values
        secret_id = secrets[0]["id"]
        values_response = await self._client.get(f"/api/v1/secrets/{secret_id}/values")
        if values_response.status_code != 200:
            return None
        
        values = values_response.json()["values"]
        return values.get(field)
    
    async def resolve_env_reference(self, ref: str) -> Optional[str]:
        """Resolve 'os.environ/OPENAI_API_KEY' style references."""
        if not ref.startswith("os.environ/"):
            return ref
        
        env_name = ref.replace("os.environ/", "")
        
        # Map env names to provider/field
        mapping = {
            "OPENAI_API_KEY": ("openai", "api_key"),
            "ANTHROPIC_API_KEY": ("anthropic", "api_key"),
            "AZURE_API_KEY": ("azure_openai", "api_key"),
            "AZURE_API_BASE": ("azure_openai", "endpoint"),
            "GROQ_API_KEY": ("groq", "api_key"),
            "DISCORD_BOT_TOKEN": ("discord", "bot_token"),
            # ... more mappings
        }
        
        if env_name not in mapping:
            import os
            return os.getenv(env_name)
        
        provider, field = mapping[env_name]
        return await self.get_secret(provider, field)
```

---

## Formato de Eventos (Redis Streams)

### AgentRequestEvent

```python
class AgentRequestEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Source info
    source: Literal["discord", "slack", "rest", "webhook", "internal"]
    source_id: str  # channel_id, conversation_id, etc.
    
    # User info
    user_id: str
    user_name: Optional[str] = None
    
    # Content
    content: str
    attachments: List[Attachment] = []
    
    # Routing
    agent_id: Optional[str] = None  # If None, use default routing
    team_id: Optional[str] = None
    workflow_id: Optional[str] = None
    
    # Session
    session_id: str
    session_state: Dict[str, Any] = {}
    
    # Reply config
    reply_stream: str  # Where to send the response
    
    # Metadata
    metadata: Dict[str, Any] = {}
```

### AgentResponseEvent

```python
class AgentResponseEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str  # Reference to original request
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Content
    content: str
    content_type: Literal["text", "structured", "error"] = "text"
    structured_data: Optional[Dict[str, Any]] = None
    
    # Status
    status: Literal["completed", "error", "timeout"] = "completed"
    error_message: Optional[str] = None
    
    # Execution info
    agent_id: str
    agent_name: str
    execution_time_ms: int
    tokens_used: Optional[int] = None
    
    # Media
    images: List[str] = []
    files: List[Dict[str, str]] = []
    
    # Metadata
    metadata: Dict[str, Any] = {}
```

---

## Routing de Eventos

### Como determinar qual Agent/Team executar?

```python
class EventRouter:
    def __init__(self, agent_manager: AgentManager, team_manager: TeamManager):
        self.agent_manager = agent_manager
        self.team_manager = team_manager
        self._routing_rules: List[RoutingRule] = []
    
    async def route(self, event: AgentRequestEvent) -> Optional[str]:
        # 1. Explicit routing (event specifies agent_id)
        if event.agent_id:
            return ("agent", event.agent_id)
        if event.team_id:
            return ("team", event.team_id)
        if event.workflow_id:
            return ("workflow", event.workflow_id)
        
        # 2. Rule-based routing
        for rule in self._routing_rules:
            if await rule.matches(event):
                return (rule.target_type, rule.target_id)
        
        # 3. Source-based default routing
        source_defaults = {
            "discord": ("agent", "discord-assistant"),
            "slack": ("agent", "slack-assistant"),
            "rest": ("agent", "default-assistant"),
        }
        return source_defaults.get(event.source, ("agent", "default-assistant"))

class RoutingRule(BaseModel):
    name: str
    priority: int = 0
    
    # Conditions
    source: Optional[str] = None
    source_id_pattern: Optional[str] = None  # Regex
    user_id: Optional[str] = None
    content_pattern: Optional[str] = None  # Regex
    metadata_match: Optional[Dict[str, Any]] = None
    
    # Target
    target_type: Literal["agent", "team", "workflow"]
    target_id: str
```

---

## Configuração por Interface

### Discord Interface Config

```yaml
# config/interfaces/discord.yaml
discord:
  token: "secret:discord:bot_token"  # Resolved via SecretsManager
  
  routing:
    default_agent: "discord-assistant"
    
    rules:
      - name: "Admin Channel"
        channel_ids: ["123456789"]
        agent_id: "admin-agent"
        
      - name: "Support Guild"
        guild_ids: ["987654321"]
        team_id: "support-team"
        
      - name: "Code Help"
        content_pattern: "^/code"
        agent_id: "code-assistant"
  
  session:
    prefix: "discord"
    ttl: 3600
```

---

## Implementação Sugerida

### 1. dynamic-agents/src/dynamic_agents/events/

```
events/
├── __init__.py
├── schemas.py          # AgentRequestEvent, AgentResponseEvent
├── consumer.py         # FastStream consumer
├── publisher.py        # FastStream publisher
├── router.py           # EventRouter
└── handlers.py         # Event handlers
```

### 2. dynamic-agents/src/dynamic_agents/secrets/

```
secrets/
├── __init__.py
├── manager.py          # SecretsManager
├── cache.py            # Local cache implementation
└── providers.py        # Provider-specific logic
```

### 3. agno-interfaces - Modificações

Adicionar suporte a roteamento configurável:

```python
# agno_interfaces/routing.py
class AgentRouting:
    def __init__(self, config: RoutingConfig):
        self.config = config
        self._publisher: Optional[FastStreamPublisher] = None
    
    async def route_event(self, event: Dict[str, Any], source: str) -> None:
        # Determine agent/team based on config
        target = self._resolve_target(event, source)
        
        # Publish to agent:requests stream
        request = AgentRequestEvent(
            source=source,
            source_id=event.get("channel_id") or event.get("conversation_id"),
            user_id=event.get("user_id"),
            content=event.get("content"),
            agent_id=target.agent_id,
            team_id=target.team_id,
            session_id=f"{source}:{event.get('channel_id')}",
            reply_stream=f"agent:responses:{source}:{event.get('channel_id')}"
        )
        
        await self._publisher.publish(request.model_dump())
```

---

## Resumo das Decisões

| Aspecto | Decisão | Justificativa |
|---------|---------|---------------|
| **Comunicação Interfaces ↔ Agents** | Redis Streams | Já usado no FastStreamInterface, desacoplado, escalável |
| **Comunicação Admin/Dashboard** | REST API | Simplicidade para CRUD e configuração |
| **Secrets** | A8N Identity via REST | Já implementado, com encriptação e RBAC |
| **Session Storage** | PostgreSQL (via Agno DB) | Consistência, queries complexas |
| **Cache** | Redis | Performance, TTL nativo |
| **Event Format** | Pydantic + JSON | Type-safe, fácil de debugar |

---

## Próximos Passos

1. **Fase 0: Secrets Integration**
   - [ ] Implementar SecretsManager no dynamic-agents
   - [ ] Integrar com LiteLLM Router
   - [ ] Testar flow completo de secrets

2. **Fase 1: Event System**
   - [ ] Definir schemas de eventos
   - [ ] Implementar consumer no dynamic-agents
   - [ ] Implementar publisher para responses

3. **Fase 2: Routing**
   - [ ] Implementar EventRouter
   - [ ] Configuração YAML de routing
   - [ ] Testar com Discord Interface

4. **Fase 3: Integration Tests**
   - [ ] E2E: Discord → dynamic-agents → response
   - [ ] E2E: REST API → agent execution
   - [ ] Load testing
