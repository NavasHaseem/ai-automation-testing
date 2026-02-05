"""
Base Tool Class
Foundation for all MCP tools
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ToolInput(BaseModel):
    """Base input for tool calls"""
    pass


class ToolOutput(BaseModel):
    """Base output for tool results"""
    success: bool
    data: Any = None
    error: Optional[str] = None


class BaseTool(ABC):
    """
    Base tool class for MCP tool definitions
    
    Subclasses should implement:
    - get_definition(): Tool schema and metadata
    - execute(): Tool execution logic
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    def get_definition(self) -> Dict[str, Any]:
        """
        Return tool definition for MCP
        Includes name, description, input schema, etc.
        """
        pass
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> ToolOutput:
        """
        Execute the tool with given input
        Returns ToolOutput with result or error
        """
        pass
    
    def get_info(self) -> Dict[str, str]:
        """Get tool metadata"""
        return {
            "name": self.name,
            "description": self.description
        }
