"""
Document Agent - Deprecated
This functionality has been integrated into the langgraph_agent.py module.
Use process_document_with_agent() directly instead.
"""
from typing import Any, Dict
from langgraph.graph import StateGraph
from .base_agent import BaseAgent, AgentState


class DocumentAgent(BaseAgent):
    """
    Deprecated: Use utils.langgraph_agent.process_document_with_agent() instead.
    
    This class is maintained for backward compatibility but no longer implements
    active workflow nodes.
    """
    
    def __init__(self):
        super().__init__(
            name="DocumentAgent",
            description="[DEPRECATED] Use langgraph_agent module instead"
        )
    
    def create_graph(self) -> StateGraph:
        """Graph creation - see langgraph_agent.py for current implementation"""
        graph = StateGraph(AgentState)
        return graph
    
    async def run(self, input_state: AgentState) -> AgentState:
        """Use process_document_with_agent() from utils.langgraph_agent instead"""
        input_state.output = f"Deprecated: {input_state.input}"
        return input_state
