"""
Base Handler Class
Foundation for MCP request handlers
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class HandlerRequest(BaseModel):
    """Base request for handlers"""
    tool_name: str
    operation: str
    params: Dict[str, Any] = {}


class HandlerResponse(BaseModel):
    """Base response from handlers"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}


class BaseHandler(ABC):
    """
    Base handler class for MCP request processing
    
    Subclasses should implement:
    - handle_request(): Process MCP requests
    """
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def handle_request(self, request: HandlerRequest) -> HandlerResponse:
        """
        Handle MCP request and return response
        TODO: Implement request routing to appropriate tools
        """
        pass
