"""
Base Agent Class
Foundation for all LangGraph agents
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from langgraph.graph import StateGraph
from pydantic import BaseModel


class AgentState(BaseModel):
    """Base state for agents"""
    input: str
    context: Dict[str, Any] = {}
    messages: List[Dict[str, str]] = []
    output: Optional[str] = None
    metadata: Dict[str, Any] = {}


class BaseAgent(ABC):
    """
    Base agent class for implementing LangGraph-based agents
    
    Subclasses should implement:
    - create_graph(): Build the LangGraph workflow
    - run(): Execute the agent
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.graph = None
        self._initialize()
    
    def _initialize(self):
        """Initialize the agent graph"""
        self.graph = self.create_graph()
    
    @abstractmethod
    def create_graph(self) -> StateGraph:
        """
        Create and return the LangGraph workflow
        Should define nodes and edges for the agent
        """
        pass
    
    @abstractmethod
    async def run(self, input_state: AgentState) -> AgentState:
        """
        Execute the agent with given input state
        Returns updated state with output
        """
        pass
    
    def get_info(self) -> Dict[str, str]:
        """Get agent metadata"""
        return {
            "name": self.name,
            "description": self.description
        }
