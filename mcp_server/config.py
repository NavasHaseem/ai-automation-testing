"""
Configuration Management for Agents and MCP Server
Environment variables and settings
"""
from pydantic_settings import BaseSettings
from typing import Optional


class AgentSettings(BaseSettings):
    """Agent configuration"""
    agent_timeout: int = 300
    agent_max_retries: int = 3
    agent_debug: bool = False
    
    class Config:
        env_prefix = "AGENT_"


class MCPServerSettings(BaseSettings):
    """MCP Server configuration"""
    mcp_server_port: int = 8002
    mcp_server_host: str = "localhost"
    mcp_debug: bool = False
    mcp_worker_threads: int = 4
    
    class Config:
        env_prefix = "MCP_"


class ToolSettings(BaseSettings):
    """Tool configuration"""
    tool_timeout: int = 60
    tool_batch_size: int = 5
    tool_retry_attempts: int = 3
    
    class Config:
        env_prefix = "TOOL_"


class Settings(BaseSettings):
    """Combined settings"""
    agent: AgentSettings = AgentSettings()
    mcp_server: MCPServerSettings = MCPServerSettings()
    tool: ToolSettings = ToolSettings()
    
    # Existing settings
    pinecone_api_key: Optional[str] = None
    mongodb_uri: Optional[str] = None
    backend_base_url: str = "http://localhost:8000"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
