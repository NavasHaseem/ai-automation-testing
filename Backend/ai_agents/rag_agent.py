"""
RAG Agent - Deprecated
RAG functionality has been integrated into the FastAPI main.py endpoints and langgraph_agent.py.
Use the following instead:
- /pinecone/query for semantic search and answer generation
- /pinecone/embed-upsert for document processing
- /postgres/query for database queries
"""
from typing import Any, Dict
from langgraph.graph import StateGraph
from .base_agent import BaseAgent, AgentState


class RAGAgent(BaseAgent):
    """
    Deprecated: RAG operations are now distributed across main.py endpoints
    and utils/langgraph_agent.py
    
    This class is maintained for backward compatibility only.
    """
    
    def __init__(self):
        super().__init__(
            name="RAGAgent",
            description="[DEPRECATED] Use main.py RAG endpoints instead"
        )
    
    def create_graph(self) -> StateGraph:
        """See main.py and langgraph_agent.py for current implementations"""
        graph = StateGraph(AgentState)
        return graph
    
    async def run(self, input_state: AgentState) -> AgentState:
        """Use FastAPI endpoints in main.py instead"""
        input_state.output = f"Deprecated: {input_state.input}"
        return input_state
