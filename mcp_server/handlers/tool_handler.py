"""
Tool Handler
Routes tool requests to appropriate tool implementations
"""
from typing import Any, Dict, Optional
from .base_handler import BaseHandler, HandlerRequest, HandlerResponse
from ..tools.jira_tool import JiraTool
from ..tools.pinecone_tool import PineconeTool
from ..tools.mongodb_tool import MongoDBTool
from ..tools.postgresql_tool import PostgreSQLTool


class ToolHandler(BaseHandler):
    """
    Handles tool execution requests
    Routes to appropriate tool based on tool_name and operation
    """
    
    def __init__(self):
        super().__init__("ToolHandler")
        self.tools = {
            "JiraTool": JiraTool(),
            "PineconeTool": PineconeTool(),
            "MongoDBTool": MongoDBTool(),
            "PostgreSQLTool": PostgreSQLTool(),
        }
    
    async def handle_request(self, request: HandlerRequest) -> HandlerResponse:
        """
        Route request to appropriate tool and execute
        TODO: Implement tool routing and execution
        """
        try:
            tool_name = request.tool_name
            
            if tool_name not in self.tools:
                return HandlerResponse(
                    success=False,
                    error=f"Tool '{tool_name}' not found"
                )
            
            tool = self.tools[tool_name]
            
            # Execute tool
            result = await tool.execute({
                "operation": request.operation,
                "params": request.params
            })
            
            return HandlerResponse(
                success=result.success,
                data=result.data,
                error=result.error,
                metadata={"tool": tool_name}
            )
            
        except Exception as e:
            return HandlerResponse(
                success=False,
                error=f"Handler error: {str(e)}"
            )
    
    def get_available_tools(self) -> Dict[str, Dict[str, str]]:
        """Get list of available tools and their info"""
        return {
            name: tool.get_info()
            for name, tool in self.tools.items()
        }
