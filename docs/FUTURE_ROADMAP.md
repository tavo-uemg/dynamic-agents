# Roadmap Futuro: Dynamic Agents

Este documento descreve as próximas etapas evolutivas para transformar o sistema `dynamic-agents` de um backend robusto em uma plataforma completa de Agentes de IA (LLMOps).

A prioridade foi definida com base no impacto imediato na usabilidade e na capacidade de depuração do sistema.

---

## 🚀 Prioridade 1: Visibilidade e Usabilidade (Curto Prazo)

Atualmente, o sistema é uma "caixa preta" acessível apenas via API. Precisamos "ver" os agentes pensando e facilitar a interação.

### 1. Interface de Usuário (Admin & Playground)
Uma interface visual para criar, gerenciar e testar agentes sem escrever JSON manualmente.

*   **Objetivo:** Permitir que usuários não técnicos criem e testem agentes.
*   **Funcionalidades:**
    *   **Builder:** Formulários visuais para configurar Agentes/Times (seleção de modelos, drag-and-drop de tools).
    *   **Playground:** Interface de chat para testar agentes em tempo real com streaming.
    *   **Monitor:** Dashboard para visualizar execuções, status do Redis e filas.
*   **Stack Sugerida:** Streamlit (MVP rápido) ou Next.js/React (Produto final).

### 2. Observabilidade e Tracing (O "Raio-X")
Logs de texto não são suficientes para entender cadeias complexas de raciocínio (Chain of Thought).

*   **Objetivo:** Visualizar cada passo do agente: input -> pensamento -> tool call -> output -> resposta final.
*   **Funcionalidades:**
    *   Rastreamento de latência e custo por passo.
    *   Visualização de árvores de execução para Workflows e Times.
    *   Histórico detalhado de erros.
*   **Stack Sugerida:** Integração com **Langfuse**, **Arize Phoenix** ou **OpenTelemetry**.
*   **Implementação:** Adicionar um `CallbackHandler` no Agno/LiteLLM para exportar telemetria.

---

## 🧠 Prioridade 2: Capacidades Cognitivas (Médio Prazo)

Expandir o que os agentes conseguem "saber" e como acessam informações.

### 3. Pipeline de RAG (Knowledge Ingestion API)
O sistema suporta configuração de Knowledge, mas falta uma via fácil para "alimentar" o cérebro dos agentes.

*   **Objetivo:** Endpoint para upload e processamento de documentos.
*   **Funcionalidades:**
    *   `POST /knowledge/ingest`: Aceitar PDF, TXT, MD, URL.
    *   **Chunking & Embedding:** Processamento automático em background (Worker).
    *   **Vector DB:** Integração nativa com `pgvector` (Postgres) ou Qdrant.
    *   Associação dinâmica: Ligar um "Knowledge Base ID" a um Agente.

---

## 🛡️ Prioridade 3: Controle e Segurança (Longo Prazo)

Necessário para colocar agentes em produção em ambientes corporativos ou sensíveis.

### 4. Human-in-the-Loop (Aprovação Humana)
Agentes não devem executar ações críticas (ex: transferências, emails em massa) sem supervisão.

*   **Objetivo:** Permitir pausas em workflows para aprovação manual.
*   **Funcionalidades:**
    *   Novo passo de Workflow: `ManualApproval`.
    *   Estado de execução: `SUSPENDED` ou `AWAITING_INPUT`.
    *   Endpoint `POST /executions/{id}/resume` para humanos aprovarem/rejeitarem e inserirem feedback.

### 5. Sandboxing de Código
Segurança para agentes que escrevem e executam código (Python/Shell).

*   **Objetivo:** Impedir que um agente acidentalmente (ou maliciosamente) danifique o servidor host.
*   **Funcionalidades:**
    *   Substituir a execução local de Python por ambientes isolados.
    *   Ambientes efêmeros que morrem após a execução.
*   **Stack Sugerida:** **E2B**, **Dagger** ou Containers Docker dinâmicos.

---

## 🔌 Prioridade 4: Ecossistema e Expansão

### 6. Marketplace de MCP (Model Context Protocol)
Facilitar a conexão com ferramentas externas sem configuração manual complexa.

*   **Objetivo:** Catálogo "Plug-and-Play" de integrações.
*   **Funcionalidades:**
    *   Registro centralizado de servidores MCP públicos (Github, Slack, Google Drive).
    *   Auto-discovery de ferramentas ao conectar um servidor MCP.
    *   Gerenciamento de credenciais (OAuth) para ferramentas MCP.

### 7. Expansão de Features do Agno (Skills & Memory)
O Agno possui funcionalidades avançadas que ainda não foram expostas na configuração dinâmica.

*   **Skills:** Diferente de Tools, Skills (ex: `LocalSkills`) carregam instruções e conhecimento especializado de arquivos.
    *   **Ação:** Adicionar campo `skills` no `AgentConfig`.
    *   **Implementação:** Suportar `LocalSkills` e loaders customizados na `AgentFactory`.
*   **MemoryTools:** Controle fino sobre a memória procedural.
    *   **Ação:** Permitir configuração explícita de `MemoryTools` além das flags booleanas simples.
*   **RAG Híbrido:** Suporte explícito para flags `search_knowledge` (Agentic) vs `add_knowledge_to_context` (Traditional) e filtros dinâmicos.

### 8. Funcionalidades Avançadas do LiteLLM (Guardrails & Budget)
O Router do LiteLLM oferece proteções que devem ser configuráveis.

*   **Guardrails:** Validação de entrada/saída (ex: Lasso, Llama Guard).
    *   **Ação:** Adicionar configuração de `guardrails` no `RouterConfig` e `ModelDeployment`.
*   **Cost-Based Routing:** Roteamento baseado no menor custo (já suportado pela string, mas requer validação).
*   **Caching Semântico:** Configuração fina de TTL e políticas de cache via metadados.

---

## Resumo da Arquitetura Alvo (v2.0)

```mermaid
graph TD
    User[Usuário / Frontend] --> API[FastAPI Gateway]
    
    subgraph "Observability Layer"
        Langfuse[Langfuse/Phoenix]
    end
    
    subgraph "Core System"
        API --> Engine[Execution Engine]
        Engine --> Redis[Redis Queue]
        Worker[Redis Worker] --> Agno[Agno Framework]
    end
    
    subgraph "Safety & Data"
        Agno --> Sandbox[Code Sandbox (E2B)]
        Agno --> VectorDB[Vector DB (RAG)]
        Agno --> Tools[Tool Registry / MCP]
    end
    
    Agno -.-> Langfuse
    API -.-> Langfuse
```
