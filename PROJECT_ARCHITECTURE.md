"""
Project Architecture Overview
Extended with Agents and MCP Server
"""

# Updated Project Structure

```
ai-automation-testing/
│
├── Backend/
│   ├── agents/                          ✨ NEW: LangGraph Agents Module
│   │   ├── __init__.py
│   │   ├── base_agent.py               # Base agent class
│   │   ├── document_agent.py           # Document processing agent
│   │   ├── query_agent.py              # Semantic search & RAG agent
│   │   └── rag_agent.py                # Comprehensive multi-source RAG
│   │
│   ├── utils/                          (Existing utilities)
│   │   ├── MangoDB.py                  (Document storage)
│   │   ├── pinecone_store.py           (Vector DB)
│   │   ├── postgres_*.py               (Database utilities)
│   │   ├── jira_api.py                 (Jira integration)
│   │   ├── langgraph_agent.py          (Existing doc workflow)
│   │   └── ...
│   │
│   ├── Models/                         (Existing models)
│   ├── main.py                         (FastAPI backend)
│   └── __init__.py
│
├── mcp_server/                          ✨ NEW: MCP Orchestrator
│   ├── server.py                       # Main MCP FastAPI server
│   │
│   ├── tools/                          # Tool implementations
│   │   ├── __init__.py
│   │   ├── base_tool.py               # Abstract tool base
│   │   ├── jira_tool.py               # Jira operations
│   │   ├── pinecone_tool.py           # Vector DB operations
│   │   ├── mongodb_tool.py            # Document operations
│   │   └── postgresql_tool.py         # Database operations
│   │
│   ├── handlers/                       # Request handlers
│   │   ├── __init__.py
│   │   ├── base_handler.py            # Abstract handler
│   │   └── tool_handler.py            # Tool routing logic
│   │
│   └── config.py                       # MCP configuration
│
├── Frontend/
│   └── app.py                          (Streamlit UI)
│
├── Documentation/
│   ├── AGENTS_MCP_STRUCTURE.md         # Detailed architecture docs
│   ├── AGENTS_MCP_QUICKSTART.md        # Quick start guide
│   ├── EXTENSION_DEPENDENCIES.md       # Required packages
│   ├── PROJECT_ARCHITECTURE.md         # This file
│   ├── PROJECT_SUMMARY.md              (Existing)
│   ├── README.md                       (Existing)
│   └── ...
│
├── pyproject.toml                      (Updated with new deps)
└── .env                                (Environment config)
```

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (Streamlit)                          │
│  - Upload documents                                              │
│  - Query interface                                               │
│  - View Jira/DB data                                             │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              Backend (FastAPI) - main.py                         │
│  - File management endpoints                                     │
│  - Document processing endpoints                                 │
│  - Query endpoints                                               │
│  - Agent invocation endpoints (NEW)                              │
└────────┬──────────────────────────────────────────────────────┬─┘
         │                                                       │
         ▼                                                       ▼
    ┌─────────────────────────────┐          ┌──────────────────────────┐
    │  LangGraph Agents           │          │  MCP Server              │
    │  (Backend/agents/)          │          │  (mcp_server/server.py)  │
    │                             │          │                          │
    │  - DocumentAgent            │          │  REST API Interface:     │
    │  - QueryAgent               │◄────────►│  - /execute              │
    │  - RAGAgent                 │          │  - /tools                │
    │  - Custom agents            │          │  - /agent/invoke         │
    │                             │          │                          │
    │  State Management:          │          │  Tool Registry:          │
    │  - Input processing         │          │  - JiraTool              │
    │  - Context building         │          │  - PineconeTool          │
    │  - Output generation        │          │  - MongoDBTool           │
    └─────────────────────────────┘          │  - PostgreSQLTool        │
         │                                   └──────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────────────────────────┐
    │           Utility Layer (Backend/utils/)                     │
    │                                                              │
    │  Data Sources:          Processing:       Integrations:      │
    │  - MangoDB              - parse_text.py   - jira_api.py      │
    │  - PostgreSQL           - chunking.py     - email            │
    │  - Pinecone             - embedding.py    - webhooks         │
    └─────────────────────────────────────────────────────────────┘
         │           │           │           │
         ▼           ▼           ▼           ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ MongoDB  │ │PostgreSQL│ │ Pinecone │ │ Jira API │
    │ + GridFS │ │+ airlines│ │ (Vector) │ │ REST     │
    └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

## Agent Processing Pipeline

```
┌─────────────────┐
│  User Input     │
│  (Query/Upload) │
└────────┬────────┘
         │
         ▼
    ┌──────────────────────┐
    │ Agent Selection      │
    │ - Document?          │
    │ - Query?             │
    │ - Multi-source?      │
    └────────┬─────────────┘
             │
    ┌────────▼─────────┬──────────────┬───────────────┐
    │                  │              │               │
    ▼                  ▼              ▼               ▼
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│Document  │    │Query     │    │RAG       │    │Custom    │
│Agent     │    │Agent     │    │Agent     │    │Agent     │
└────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘
     │               │               │             │
     ├───────────────┼───────────────┼─────────────┤
     │
     ▼
┌─────────────────────────────────┐
│  LangGraph Workflow Execution   │
│                                 │
│  Graph Nodes:                   │
│  1. Analyze/Validate Input      │
│  2. Retrieve Context (MCP Tools)│
│  3. Process/Transform           │
│  4. Generate Response           │
│  5. Return Output               │
└────────┬────────────────────────┘
         │
         ▼
    ┌─────────────────┐
    │ Output/Result   │
    │ - Document ID   │
    │ - Query Answer  │
    │ - Metadata      │
    └─────────────────┘
```

## Tool Integration Pattern

```
Agent Workflow
    │
    ├─ Node 1: Needs data
    │   └─ Calls MCP Tool Handler
    │       └─ Routes to specific tool
    │           └─ Tool executes operation
    │               └─ Returns ToolOutput
    │                   └─ Node processes result
    │
    ├─ Node 2: Needs transformation
    │   └─ Calls MCP Tool (e.g., Pinecone)
    │       └─ Tool executes embedding/search
    │           └─ Returns results
    │
    └─ Node 3: Generates final output
        └─ Synthesizes results
            └─ Returns to user
```

## Recent Architecture Improvements (February 2026)

### Environment Management
- **Central Configuration**: `.env` file at project root for reliable loading across all modules
- **DotEnv Strategy**: Uses `load_dotenv(find_dotenv())` for proper .env discovery
- **Module Configuration**: Individual utils modules safely load environment variables

### Import Resolution
- **Backend Package Structure**: All modules use `from Backend.utils.*` imports (not relative imports)
- **Module Independence**: Each utility module can be imported directly or from main app
- **Fixed Files**: 
  - `langgraph_agent.py`: Updated all 4 import statements to use `Backend.utils` prefix
  - `MangoDB.py`: Uses `find_dotenv()` for environment discovery

### Vector Database Management
- **Namespace Operations**: Added `delete_namespace()` function to `pinecone_store.py`
- **Cleanup Utilities**: `delete_namespace.py` script for managing vector namespaces
- **Namespace Structure**:
  - `mongodb-files`: Document embeddings
  - `postgresql-data`: PostgreSQL row embeddings
  - `default`: General-purpose vectors

## Deployment Architecture

### Development
```
localhost:8000  (Backend API + Agent endpoints)
localhost:8002  (MCP Server)
localhost:8501  (Streamlit Frontend)
```

### Production
```
api.service/        (Backend API)
mcp.service/        (MCP Server)
ui.service/         (Streamlit Frontend)
```

## Communication Patterns

### Pattern 1: Direct Agent Use (Backend)
```python
from Backend.agents.query_agent import QueryAgent

agent = QueryAgent()
result = await agent.run(state)
```

### Pattern 2: MCP Tool Use (Distributed)
```bash
curl -X POST http://mcp-server:8002/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "PineconeTool", ...}'
```

### Pattern 3: Agent + MCP Integration (Advanced)
```python
# Agent calls MCP tools via HTTP
async def agent_node(state):
    result = await call_mcp_tool("PineconeTool", "search", params)
    state.context['search_results'] = result
    return state
```

## Scaling Considerations

### Single Server Setup
- Backend, Agents, and MCP on same server
- Suitable for development and small deployments

### Distributed Setup
- Backend API separate
- MCP Server separate (enables horizontal scaling)
- Frontend separate (CDN capable)

### Load Balancing
- Multiple MCP instances behind load balancer
- Agent queuing system for high concurrency
- Tool caching for frequent operations

## Configuration Management

Configured via `.env`:
```env
# Agents
AGENT_TIMEOUT=300
AGENT_MAX_RETRIES=3

# MCP Server
MCP_SERVER_PORT=8002
MCP_SERVER_HOST=0.0.0.0

# Tools
TOOL_TIMEOUT=60
TOOL_BATCH_SIZE=5
```

See [mcp_server/config.py](mcp_server/config.py) for all settings.

## Next Steps

1. ✅ Structure created - ready for implementation
2. 📝 Implement agent workflows (see AGENTS_MCP_QUICKSTART.md)
3. 🔧 Implement tool handlers
4. 🧪 Add integration tests
5. 📊 Add monitoring and logging
6. 🚀 Deploy and scale

---

**Last Updated**: February 4, 2026
**Version**: 1.2.0 - Environment Setup & Import Fixes Complete

### Recent Fixes Summary
- ✅ Fixed environment variable loading with central `.env` file
- ✅ Corrected module imports from `utils.*` to `Backend.utils.*`
- ✅ Added vector namespace management and cleanup utilities
- ✅ Verified MongoDB file uploads and Pinecone indexing
- ✅ Confirmed working backend/frontend setup
