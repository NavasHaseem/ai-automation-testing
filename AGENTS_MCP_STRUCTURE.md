"""
Documentation for Project Extensions
Agents and MCP Server Structure
"""

# Project Structure Overview

```
ai-automation-testing/
├── Backend/
│   ├── agents/                      # NEW: LangGraph Agents
│   │   ├── __init__.py
│   │   ├── base_agent.py           # Base agent class
│   │   ├── document_agent.py       # Document processing agent
│   │   ├── query_agent.py          # Query/RAG agent
│   │   └── rag_agent.py            # Comprehensive RAG agent
│   ├── utils/
│   ├── Models/
│   └── main.py
│
├── mcp_server/                      # NEW: MCP Orchestrator Server
│   ├── server.py                   # Main MCP server
│   ├── tools/                      # Tool implementations
│   │   ├── __init__.py
│   │   ├── base_tool.py           # Base tool class
│   │   ├── jira_tool.py           # Jira integration
│   │   ├── pinecone_tool.py       # Vector DB operations
│   │   ├── mongodb_tool.py        # Document operations
│   │   └── postgresql_tool.py     # Database operations
│   └── handlers/                   # Request handlers
│       ├── __init__.py
│       ├── base_handler.py        # Base handler class
│       └── tool_handler.py        # Tool routing handler
│
├── Frontend/
└── README.md
```

## Agents Module

### Purpose
Implements LangGraph-based agents for intelligent document processing and RAG workflows.

### Classes

#### BaseAgent (base_agent.py)
- Abstract base class for all agents
- Defines agent interface with LangGraph integration
- Methods:
  - `create_graph()`: Build the state machine workflow
  - `run()`: Execute agent with input state
  - `get_info()`: Return agent metadata

#### DocumentAgent (document_agent.py)
- Handles document processing and indexing
- Operations:
  - Extract text from documents
  - Generate embeddings
  - Upsert to Pinecone
  - Update metadata
- **Status**: Scaffold ready for implementation

#### QueryAgent (query_agent.py)
- Performs semantic search and answer generation
- Operations:
  - Embed user query
  - Search Pinecone across namespaces
  - Retrieve context
  - Generate answer via LLM
- **Status**: Scaffold ready for implementation

#### RAGAgent (rag_agent.py)
- Comprehensive agent combining document and query operations
- Multi-source retrieval (documents, PostgreSQL, Jira)
- Context synthesis
- Answer generation
- **Status**: Scaffold ready for implementation

### Implementation Guide

1. **Implement create_graph()**:
   ```python
   def create_graph(self) -> StateGraph:
       graph = StateGraph(AgentState)
       
       # Add nodes
       graph.add_node("node_name", node_function)
       
       # Add edges
       graph.add_edge("start", "node_name")
       graph.add_conditional_edges("node_name", routing_function, {...})
       
       # Compile
       return graph.compile()
   ```

2. **Implement run()**:
   - Execute the compiled graph with input state
   - Handle async operations
   - Return updated state with results

## MCP Server Module

### Purpose
Model Context Protocol (MCP) server for tool orchestration and integration with external services.

### Architecture

```
Client Request
    ↓
MCP Server (server.py)
    ↓
Tool Handler (tool_handler.py)
    ↓
Tool Implementation (jira_tool.py, etc.)
    ↓
External Service / Database
```

### Server (mcp_server/server.py)
- FastAPI-based MCP server
- Endpoints:
  - `GET /health`: Health check
  - `GET /tools`: List all tools
  - `GET /tools/{tool_name}`: Get tool info
  - `POST /execute`: Execute single tool
  - `POST /execute-batch`: Execute multiple tools
  - `POST /agent/invoke`: Invoke agents (future)

### Tools

#### BaseTool (tools/base_tool.py)
- Abstract base for all MCP tools
- Methods:
  - `get_definition()`: Return tool schema for MCP
  - `execute()`: Execute tool operation
  - `get_info()`: Tool metadata

#### JiraTool (tools/jira_tool.py)
- Jira REST API operations
- Operations: search, create, update, get
- Integrates with existing `utils/jira_api.py`
- **Status**: Scaffold ready for implementation

#### PineconeTool (tools/pinecone_tool.py)
- Vector database operations
- Operations: search, upsert, delete, query
- Integrates with existing `utils/pinecone_store.py`
- **Status**: Scaffold ready for implementation

#### MongoDBTool (tools/mongodb_tool.py)
- Document storage operations
- Operations: upload, query, update, delete
- Integrates with existing `utils/MangoDB.py`
- **Status**: Scaffold ready for implementation

#### PostgreSQLTool (tools/postgresql_tool.py)
- Database operations and indexing
- Operations: query, index, schema, extract
- Integrates with existing `utils/postgres*.py`
- **Status**: Scaffold ready for implementation

### Handlers

#### BaseHandler (handlers/base_handler.py)
- Abstract base for request handlers
- Interface for processing MCP requests

#### ToolHandler (handlers/tool_handler.py)
- Routes tool execution requests
- Maintains registry of available tools
- Dispatches to appropriate tool implementation

## Integration Points

### With Existing Backend
- Reuse existing utilities (MangoDB, pinecone_store, postgres utilities)
- Wrap existing functions with MCP tool interface
- Maintain backward compatibility

### With Frontend
- Update FastAPI main.py to integrate MCP server
- Add agent invocation endpoints
- Support tool discovery and execution

### With LangGraph
- Agents use LangGraph for workflow orchestration
- Tools used by agents for external integrations
- MCP server exposes tools for CLI/external access

## Setup & Running

### 1. Start MCP Server
```bash
cd mcp_server
python server.py
# Server runs on http://localhost:8002
```

### 2. Use Tools via MCP
```bash
# List available tools
curl http://localhost:8002/tools

# Execute tool
curl -X POST http://localhost:8002/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "PineconeTool",
    "operation": "search",
    "params": {...}
  }'
```

### 3. Use Agents
```python
from Backend.agents.rag_agent import RAGAgent

agent = RAGAgent()
state = AgentState(input="Your query")
result = await agent.run(state)
```

## Next Steps

1. **Implement Agent Workflows**:
   - Define nodes for each agent
   - Implement node functions
   - Set up conditional routing
   - Test agent execution

2. **Implement Tool Handlers**:
   - Wrap existing utility functions
   - Add error handling
   - Validate input parameters
   - Test tool execution

3. **Integration Testing**:
   - Test agent→tool communication
   - Test MCP server endpoints
   - Test batch operations
   - Performance testing

4. **UI Integration**:
   - Add agent invocation to Frontend
   - Add tool discovery UI
   - Show execution results
   - Error handling and logging

## Configuration

Add to `.env`:
```env
# MCP Server
MCP_SERVER_PORT=8002
MCP_SERVER_HOST=localhost

# Agent Configuration
AGENT_TIMEOUT=300
AGENT_MAX_RETRIES=3

# Tool Configuration
TOOL_TIMEOUT=60
TOOL_BATCH_SIZE=5
```

Update `pyproject.toml` dependencies (see EXTENSION_DEPENDENCIES.md for required packages).
