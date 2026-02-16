"""
Extension Dependencies
Additional packages needed for Agents and MCP Server
"""

# Required Dependencies

## For Agents (LangGraph)
- langgraph >= 0.2.0          (already in pyproject.toml)
- langchain-core >= 1.1.0     (already in pyproject.toml)
- langchain-openai >= 0.2.0   (already in pyproject.toml)

## For MCP Server
- fastapi >= 0.100.0          (for REST API)
- uvicorn >= 0.23.0           (for server)
- pydantic >= 2.0.0           (for data validation)

## Additional Recommended
- pydantic-settings >= 2.0.0  (for env config)
- python-dotenv >= 1.2.1      (already in pyproject.toml)

# Update to pyproject.toml

Add these to the dependencies list:

```toml
[project]
name = "ai-testing"
version = "0.2.0"
description = "RAG implementation with LangGraph agents and MCP orchestrator"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    # Existing dependencies
    "langgraph>=0.2.0",
    "langchain-core>=1.1.0",
    "langchain-openai>=0.2.0",
    "python-dotenv>=1.2.1",
    "streamlit>=1.52.0",
    
    # New dependencies for extensions
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    
    # Existing backend dependencies (likely already installed)
    "pymongo>=4.0.0",
    "pinecone-client>=2.0.0",
    "PyMuPDF>=1.23.0",
    "python-docx>=0.8.11",
    "requests>=2.28.0",
]
```

# Installation

```bash
pip install -e .
```

Or install individually:

```bash
pip install fastapi uvicorn pydantic pydantic-settings
```
