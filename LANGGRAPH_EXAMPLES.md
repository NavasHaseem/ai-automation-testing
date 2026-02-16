# LangGraph Agent Examples

This document provides examples of how the LangGraph agents work in this project.

## Document Processing Agent

### Example 1: Small Document

**Input:**
```python
document_text = "This is a short test document."
filename = "test.txt"
file_id = "507f1f77bcf86cd799439011"
```

**Agent Decision:**
- Strategy: `single_chunk`
- Chunk Size: 31 characters
- Overlap: 0
- Reasoning: Document is < 1000 characters, process as single unit

### Example 2: Structured Document

**Input:**
```python
document_text = """
# Introduction
This is a long document with sections...

## Section 1
Content here...

## Section 2
More content...
"""
filename = "report.md"
file_id = "507f1f77bcf86cd799439012"
```

**Agent Decision:**
- Strategy: `section_based`
- Chunk Size: 1500 characters
- Overlap: 200 characters
- Reasoning: Document has clear section markers (`#`, `##`)

### Example 3: Large Unstructured Document

**Input:**
```python
document_text = "A very long continuous text without clear sections..." * 100
filename = "essay.txt"
file_id = "507f1f77bcf86cd799439013"
```

**Agent Decision:**
- Strategy: `fixed_size`
- Chunk Size: 1200 characters
- Overlap: 150 characters
- Reasoning: Long document without structural markers

## Query Agent

### Example 1: Basic Semantic Search

**Input:**
```python
query_text = "How do I configure authentication?"
namespace = "mongodb-files"
top_k = 5
```

**Agent Workflow:**
1. Embeds query → `[0.123, 0.456, ...]` (1024-dim vector)
2. Builds filter → `{"source": {"$eq": "mongodb"}}`
3. Searches Pinecone → Returns top 5 matches

### Example 2: Jira-Context Search

**Input:**
```python
query_text = "API rate limiting issues"
namespace = "mongodb-files"
top_k = 5
jira_context = {
    "project": "PROJ-123",
    "labels": ["backend", "performance"]
}
```

**Agent Workflow:**
1. Embeds query → `[0.789, 0.012, ...]`
2. Builds intelligent filter:
   ```python
   {
       "source": {"$eq": "mongodb"},
       "jira_project": {"$eq": "PROJ-123"},
       "jira_labels": {"$in": ["backend", "performance"]}
   }
   ```
3. Searches with context → Returns relevant results filtered by Jira metadata

## API Usage Examples

### Upload and Process with Agent

```bash
# 1. Upload document
curl -X POST http://localhost:8000/files/upload \
  -F "file=@document.pdf" \
  -F "tags=testing,documentation" \
  -F "notes=Test file" \
  -F "token=your-token"

# Response: {"file_id": "507f1f77bcf86cd799439011"}

# 2. Process with LangGraph agent
curl -X POST http://localhost:8000/pinecone/embed-upsert \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "file_id": "507f1f77bcf86cd799439011",
    "namespace": "mongodb-files"
  }'

# Response:
# {
#   "upserted": 5,
#   "model": "llama-text-embed-v2",
#   "dimension": 1024,
#   "agent_analysis": "Document: document.pdf\nLength: 450 words...",
#   "chunk_strategy": "fixed_size"
# }
```

### Query with Agent

```bash
curl -X POST http://localhost:8000/pinecone/query \
  -H "Content-Type: application/json" \
  -d '{
    "text": "authentication configuration",
    "namespace": "mongodb-files",
    "top_k": 3,
    "filter": {
      "jira_context": {
        "project": "AUTH-100",
        "labels": ["security"]
      }
    }
  }'

# Response:
# {
#   "matches": [
#     {
#       "id": "507f...-0",
#       "score": 0.92,
#       "metadata": {
#         "filename": "auth-guide.pdf",
#         "chunk_id": 0,
#         "text_preview": "To configure authentication..."
#       }
#     }
#   ],
#   "query": "authentication configuration"
# }
```

## Python SDK Usage

### Direct Agent Usage

```python
from utils.langgraph_agent import process_document_with_agent, query_with_agent

# Process document
result = process_document_with_agent(
    document_text="Your document content here...",
    filename="example.txt",
    file_id="507f1f77bcf86cd799439011",
    metadata={"source": "internal"}
)

print(f"Strategy: {result['chunk_strategy']}")
print(f"Chunks: {len(result['chunks'])}")
print(f"Analysis: {result['analysis']}")

# Query with agent
matches = query_with_agent(
    query_text="How to setup MongoDB?",
    namespace="mongodb-files",
    top_k=5,
    jira_context={"project": "DB-100"}
)

for match in matches:
    print(f"Score: {match['score']:.3f}")
    print(f"File: {match['metadata']['filename']}")
    print(f"Preview: {match['metadata']['text_preview'][:100]}...")
```

## Benefits of LangGraph Approach

1. **Intelligent Adaptation**: Agent analyzes each document and selects optimal processing
2. **Explainable**: Each decision is tracked in the state
3. **Extensible**: Easy to add new nodes (e.g., OCR, translation)
4. **Debuggable**: Full state history available for troubleshooting
5. **Composable**: Can chain agents for complex workflows

## State Inspection

```python
# Inspect full agent state
from utils.langgraph_agent import create_document_processing_graph

graph = create_document_processing_graph()
state = graph.invoke({
    "document_text": "Sample text",
    "filename": "test.txt",
    "file_id": "123",
    # ... other fields
})

# Examine decisions
print(f"Step: {state['step']}")
print(f"Strategy: {state['chunk_strategy']}")
print(f"Chunk size: {state['chunk_size']}")
print(f"Overlap: {state['chunk_overlap']}")
print(f"Error: {state['error']}")
```

## Advanced: Custom Nodes

You can extend the graph with custom processing nodes:

```python
def custom_preprocessing_node(state):
    """Custom node for specialized preprocessing."""
    text = state["document_text"]
    
    # Your custom logic here
    cleaned_text = text.strip().lower()
    
    return {
        **state,
        "document_text": cleaned_text,
        "step": "preprocessed"
    }

# Add to graph
workflow.add_node("preprocess", custom_preprocessing_node)
workflow.add_edge("preprocess", "analyze")
workflow.set_entry_point("preprocess")
```
