"""
Quick Start Guide for Agents and MCP Server
"""

# Quick Start: Implementing Your First Agent

## Step 1: Create Your Agent

**Example: Implement QueryAgent**

File: `Backend/agents/query_agent.py`

```python
from langgraph.graph import StateGraph, END
from .base_agent import BaseAgent, AgentState

class QueryAgent(BaseAgent):
    
    def create_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)
        
        # Define node functions
        async def embed_query(state: AgentState) -> AgentState:
            # Embed the query using Pinecone
            state.context['embedding'] = embed_texts([state.input])[0]
            return state
        
        async def search_pinecone(state: AgentState) -> AgentState:
            # Search Pinecone
            results = query(
                vector=state.context['embedding'],
                namespace="all",
                top_k=5
            )
            state.context['search_results'] = results
            return state
        
        async def generate_answer(state: AgentState) -> AgentState:
            # Use LLM to generate answer
            context = format_search_results(state.context['search_results'])
            answer = llm.generate_answer(state.input, context)
            state.output = answer
            return state
        
        # Add nodes
        graph.add_node("embed_query", embed_query)
        graph.add_node("search_pinecone", search_pinecone)
        graph.add_node("generate_answer", generate_answer)
        
        # Add edges
        graph.add_edge("start", "embed_query")
        graph.add_edge("embed_query", "search_pinecone")
        graph.add_edge("search_pinecone", "generate_answer")
        graph.add_edge("generate_answer", END)
        
        return graph.compile()
    
    async def run(self, input_state: AgentState) -> AgentState:
        return await self.graph.ainvoke(input_state)
```

## Step 2: Test Your Agent

```python
from Backend.agents.query_agent import QueryAgent
from Backend.agents.base_agent import AgentState

# Initialize agent
agent = QueryAgent()

# Create input state
state = AgentState(
    input="How do I configure MongoDB?"
)

# Run agent
result = await agent.run(state)
print(result.output)
```

---

# Quick Start: Implementing Your First Tool

## Step 1: Create Your Tool

**Example: Implement PineconeTool**

File: `mcp_server/tools/pinecone_tool.py`

```python
from typing import Any, Dict
from .base_tool import BaseTool, ToolOutput
from Backend.utils.pinecone_store import query as pinecone_query, upsert_chunks

class PineconeTool(BaseTool):
    
    async def execute(self, input_data: Dict[str, Any]) -> ToolOutput:
        try:
            operation = input_data.get("operation")
            params = input_data.get("params", {})
            
            if operation == "search":
                results = pinecone_query(
                    vector=params.get("vector"),
                    namespace=params.get("namespace", "all"),
                    top_k=params.get("top_k", 5)
                )
                return ToolOutput(success=True, data=results)
            
            elif operation == "upsert":
                result = upsert_chunks(
                    chunks=params.get("chunks"),
                    namespace=params.get("namespace")
                )
                return ToolOutput(success=True, data=result)
            
            else:
                return ToolOutput(
                    success=False,
                    error=f"Unknown operation: {operation}"
                )
        except Exception as e:
            return ToolOutput(success=False, error=str(e))
```

## Step 2: Test Your Tool via MCP

```bash
# Start MCP server
python mcp_server/server.py

# In another terminal, test tool
curl -X POST http://localhost:8002/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "PineconeTool",
    "operation": "search",
    "params": {
      "vector": [0.1, 0.2, 0.3, ...],
      "namespace": "mongodb-files",
      "top_k": 5
    }
  }'
```

---

# Integration: Connect Agent to MCP Tools

```python
from Backend.agents.base_agent import BaseAgent, AgentState
from langgraph.graph import StateGraph, END

class IntegratedAgent(BaseAgent):
    
    def __init__(self, mcp_server_url: str = "http://localhost:8002"):
        self.mcp_url = mcp_server_url
        super().__init__("IntegratedAgent", "Agent with MCP tool integration")
    
    async def call_mcp_tool(self, tool_name: str, operation: str, params: dict):
        """Call MCP tool"""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.mcp_url}/execute",
                json={
                    "tool_name": tool_name,
                    "operation": operation,
                    "params": params
                }
            )
            return response.json()
    
    def create_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)
        
        async def call_tool_node(state: AgentState):
            # Call MCP tool
            result = await self.call_mcp_tool(
                tool_name="PineconeTool",
                operation="search",
                params=state.context.get("tool_params", {})
            )
            state.context['tool_result'] = result
            return state
        
        graph.add_node("call_tool", call_tool_node)
        graph.add_edge("start", "call_tool")
        graph.add_edge("call_tool", END)
        
        return graph.compile()
```

---

# Common Patterns

## Pattern 1: Sequential Tool Calls

```python
async def multi_step_agent(state: AgentState):
    # Step 1: Search documents
    search_result = await call_mcp_tool(
        "PineconeTool", "search", {"vector": [...]}
    )
    
    # Step 2: Fetch from MongoDB
    mongo_result = await call_mcp_tool(
        "MongoDBTool", "query", {"filter": {...}}
    )
    
    # Step 3: Synthesize results
    state.output = synthesize(search_result, mongo_result)
    return state
```

## Pattern 2: Conditional Routing

```python
def route_by_input_type(state: AgentState) -> str:
    if "database" in state.input.lower():
        return "db_route"
    else:
        return "search_route"

graph.add_conditional_edges(
    "analyze_input",
    route_by_input_type,
    {"db_route": "query_db", "search_route": "search_docs"}
)
```

## Pattern 3: Error Handling

```python
async def safe_tool_call(agent, tool_name: str, operation: str, params: dict):
    try:
        result = await agent.call_mcp_tool(tool_name, operation, params)
        if not result.get('success'):
            raise Exception(result.get('error', 'Tool execution failed'))
        return result['data']
    except Exception as e:
        print(f"Tool error: {e}")
        return None
```

---

# Useful Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- Project: [AGENTS_MCP_STRUCTURE.md](AGENTS_MCP_STRUCTURE.md)
