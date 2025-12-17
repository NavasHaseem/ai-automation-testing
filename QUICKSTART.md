# Quick Start Guide - LangGraph AI Testing

## Prerequisites
- Python 3.12+
- MongoDB running
- Pinecone account

## Installation (5 minutes)

### 1. Install Dependencies
```powershell
pip install langgraph langchain-core langchain-openai python-dotenv streamlit fastapi uvicorn pymongo pinecone-client PyMuPDF python-docx pydantic requests
```

### 2. Configure Environment
Create `.env` file:
```env
# Pinecone
PINECONE_API_KEY=your_key_here
PINECONE_INDEX=your_index_name

# MongoDB
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB=filedb

# Optional Auth
API_AUTH_TOKEN=your_token_here
```

### 3. Start Services

**Terminal 1 - Backend:**
```powershell
cd Backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```powershell
cd Frontend
streamlit run app.py
```

## First Test (2 minutes)

### 1. Upload a Document
- Open http://localhost:8501
- Go to "Upload" section
- Upload a `.txt`, `.pdf`, or `.docx` file
- Add tags: `test, demo`
- Click "Upload"
- Copy the `file_id` from response

### 2. Process with LangGraph Agent
- Go to "Embed & Upsert & Query" section
- Paste the `file_id`
- Click "Embed & Upsert"

**What happens:**
1. ✅ Agent analyzes your document
2. ✅ Selects optimal chunking strategy
3. ✅ Creates intelligent chunks
4. ✅ Generates embeddings
5. ✅ Stores in Pinecone

**Response includes:**
```json
{
  "upserted": 3,
  "model": "llama-text-embed-v2",
  "dimension": 1024,
  "agent_analysis": "Document: test.txt\nLength: 150 words, 850 characters\nHas sections: false",
  "chunk_strategy": "single_chunk"
}
```

### 3. Query Your Document
- In the same section, scroll down
- Enter query: `"What is this document about?"`
- Click "Search"

**What happens:**
1. ✅ Agent embeds your query
2. ✅ Builds smart filters
3. ✅ Searches vector database
4. ✅ Returns relevant chunks with scores

## Understanding Agent Decisions

### Small Documents (< 1000 chars)
```
Strategy: single_chunk
Reasoning: No need to split small content
```

### Documents with Sections
```
Strategy: section_based
Chunk Size: 1500 chars
Overlap: 200 chars
Reasoning: Preserve section boundaries
```

### Large Unstructured Text
```
Strategy: fixed_size
Chunk Size: 1200 chars
Overlap: 150 chars
Reasoning: Balanced chunks for long content
```

## API Quick Reference

### Upload
```bash
curl -X POST http://localhost:8000/files/upload \
  -F "file=@document.pdf" \
  -F "tags=test" \
  -F "token=your_token"
```

### Embed with Agent
```bash
curl -X POST http://localhost:8000/pinecone/embed-upsert \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"file_id": "YOUR_FILE_ID", "namespace": "mongodb-files"}'
```

### Query with Agent
```bash
curl -X POST http://localhost:8000/pinecone/query \
  -H "Content-Type: application/json" \
  -d '{"text": "your query", "namespace": "mongodb-files", "top_k": 5}'
```

## Troubleshooting

**Backend won't start:**
```powershell
# Check if port 8000 is free
netstat -ano | findstr :8000

# Check MongoDB is running
mongod --version
```

**Agent import errors:**
```powershell
# Verify installation
python -c "import langgraph; print('LangGraph:', langgraph.__version__)"
python -c "from langchain_core.messages import HumanMessage; print('✅ LangChain Core OK')"
```

**Pinecone errors:**
```powershell
# Verify API key
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('API Key set:', bool(os.getenv('PINECONE_API_KEY')))"
```

## Next Steps

1. **Explore Examples**: See [LANGGRAPH_EXAMPLES.md](LANGGRAPH_EXAMPLES.md)
2. **Visualize Workflows**: Run `python Backend/utils/visualize_graph.py`
3. **Read Migration Guide**: See [LANGGRAPH_MIGRATION.md](LANGGRAPH_MIGRATION.md)
4. **Full Documentation**: See [README.md](README.md)

## Common Workflows

### Batch Processing
```python
from utils.langgraph_agent import process_document_with_agent
from utils.MangoDB import list_files

# Get all files
files = list_files(limit=100)

# Process each with agent
for file in files:
    result = process_document_with_agent(
        document_text=file['text'],
        filename=file['filename'],
        file_id=file['_id']
    )
    print(f"{file['filename']}: {result['chunk_strategy']}")
```

### Smart Search
```python
from utils.langgraph_agent import query_with_agent

# Search with Jira context
results = query_with_agent(
    query_text="authentication issues",
    namespace="mongodb-files",
    top_k=5,
    jira_context={
        "project": "SEC-100",
        "labels": ["security", "auth"]
    }
)

for r in results:
    print(f"{r['score']:.3f} - {r['metadata']['filename']}")
```

---

**Ready to go! 🚀**

Your AI Automation Testing system is now powered by intelligent LangGraph agents.
