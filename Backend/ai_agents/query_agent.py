"""
Query Agent - Deprecated
This functionality has been integrated into Backend/main.py endpoints.
Use /pinecone/query endpoint instead.
"""
from typing import Any, Dict
from langgraph.graph import StateGraph
from .base_agent import BaseAgent, AgentState


class QueryAgent(BaseAgent):
    """
    Deprecated: Query operations are now implemented in main.py /pinecone/query endpoint.
    
    This class is maintained for backward compatibility only.
    """
    
    def __init__(self):
        super().__init__(
            name="QueryAgent",
            description="[DEPRECATED] Use /pinecone/query endpoint instead"
        )
    
    def create_graph(self) -> StateGraph:
        """Graph creation - see main.py query_endpoint for current implementation"""
        graph = StateGraph(AgentState)
        return graph
    
    async def run(self, input_state: AgentState) -> AgentState:
        """Use /pinecone/query endpoint in main.py instead"""
        input_state.output = f"Deprecated: {input_state.input}"
        return input_state
