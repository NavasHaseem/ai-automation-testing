# PostgreSQL RAG Implementation

## Overview
Implemented a complete RAG (Retrieval Augmented Generation) pipeline for PostgreSQL data. Now ALL data sources (documents + PostgreSQL) are indexed in Pinecone and queried through unified semantic search.

## What Was Implemented

### 1. PostgreSQL Indexing Pipeline (`Backend/utils/postgres_indexer.py`)

**Functions:**
- `table_row_to_text()` - Converts database rows to text representations
- `chunk_table_data()` - Groups rows into chunks (default: 5 rows per chunk)
- `index_table_to_pinecone()` - Indexes a specific table into Pinecone
- `index_all_tables_to_pinecone()` - Indexes all tables in the database
- `search_postgres_data_in_pinecone()` - Searches PostgreSQL data via Pinecone

**Features:**
- Configurable chunk size (rows per vector)
- Automatic text conversion for all data types
- Metadata preservation (table name, row IDs, timestamps)
- Full text storage for LLM context
- Namespace support (`postgresql-data` by default)

### 2. API Endpoints (`Backend/main.py`)

#### New Endpoint: `/postgres/index`
```http
POST /postgres/index
Headers: Authorization: Bearer {token}

Request Body:
{
  "table_name": "airlines",        // Optional - specific table or null for all
  "namespace": "postgresql-data",  // Pinecone namespace
  "chunk_size": 5,                 // Rows per chunk
  "limit_per_table": 1000,         // Optional limit
  "exclude_tables": []             // Tables to skip
}

Response:
{
  "status": "success",
  "tables_processed": 3,
  "total_rows": 150,
  "total_chunks": 30,
  "total_vectors": 30,
  "namespace": "postgresql-data",
  "table_results": [...]
}
```

#### Updated Endpoint: `/pinecone/query`
Now supports unified search across all data sources:

```http
POST /pinecone/query

Request:
{
  "namespace": "all",              // "all", "mongodb-files", or "postgresql-data"
  "top_k": 5,
  "filter": {},
  "text": "What airlines operate in the USA?"
}

Response:
{
  "status": "success",
  "matches": [...],                // Matches from both sources
  "total_results": 8,
  "answer": "Based on the database...",  // LLM-generated answer
  "postgres_data": {
    "source": "pinecone_rag",
    "record_count": 3,
    "message": "Retrieved from Pinecone vector database"
  }
}
```

### 3. Frontend Updates (`Frontend/app.py`)

**New Tab in PostgreSQL Section:**
- **"Index to Pinecone (RAG)"** - Index PostgreSQL tables into Pinecone
  - Option to index all tables or specific table
  - Configurable chunk size and row limits
  - Real-time progress metrics
  - Detailed results table

**Updated Query Interface:**
- Changed namespace dropdown to support "all", "mongodb-files", "postgresql-data"
- Updated labels to reflect unified RAG system
- Added help text explaining the search scope

### 4. Data Models (`Backend/Models/Model.py`)

**New Models:**
```python
class PostgresIndexRequest(BaseModel):
    table_name: Optional[str] = None
    namespace: str = "postgresql-data"
    chunk_size: int = 5
    limit_per_table: Optional[int] = None
    exclude_tables: Optional[List[str]] = None

class PostgresIndexResponse(BaseModel):
    status: str
    tables_processed: int
    total_rows: int
    total_chunks: int
    total_vectors: int
    namespace: str
    table_results: Optional[List[Dict[str, Any]]] = None
```

**Updated Models:**
```python
class QueryRequest(BaseModel):
    namespace: str = "all"  # Now defaults to "all"
    ...
```

## Architecture Changes

### Before (Hybrid Approach)
```
Query → Embed → [Pinecone Search] + [Direct PostgreSQL SQL] → Merge → LLM → Answer
                      ↓                      ↓
                  Documents            PostgreSQL DB
```

### After (Pure RAG)
```
Indexing:
PostgreSQL → Extract → Chunk → Embed → Pinecone (namespace: postgresql-data)
Documents  → Extract → Chunk → Embed → Pinecone (namespace: mongodb-files)

Querying:
Query → Embed → Pinecone Search (both namespaces) → LLM → Answer
                       ↓
              Unified Vector Database
```

## How to Use

### Step 1: Index PostgreSQL Data

1. Navigate to **PostgreSQL Data** section
2. Go to **"Index to Pinecone (RAG)"** tab
3. Choose indexing option:
   - **All Tables**: Indexes entire database
   - **Specific Table**: Select from dropdown
4. Configure settings:
   - Chunk size (rows per vector): 5 recommended
   - Row limit (optional): For testing with large tables
5. Click **"🚀 Index to Pinecone"**
6. Wait for completion (may take minutes for large tables)
7. Review metrics: tables processed, rows, chunks, vectors

### Step 2: Query Unified RAG System

1. Navigate to **Embed & Upsert & Query** section
2. Go to query tab
3. Select search scope:
   - **all**: Searches documents + PostgreSQL
   - **mongodb-files**: Only documents
   - **postgresql-data**: Only PostgreSQL
4. Enter your question
5. Click **"Search"**
6. View AI-generated answer with source attribution

### Step 3: Re-index When Data Changes

When PostgreSQL data is updated:
1. Re-run the indexing for affected tables
2. Vectors will be upserted (updated or inserted)
3. Queries will immediately reflect new data

## Example Workflow

```bash
# 1. Start backend (if not running)
cd Backend
..\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000

# 2. Start frontend (if not running)
cd Frontend
streamlit run app.py

# 3. In browser (http://localhost:8501):
#    - Go to PostgreSQL Data → Index to Pinecone
#    - Index all tables (or specific tables)
#    - Wait for completion
#
#    - Go to Embed & Upsert & Query → Query
#    - Set namespace to "all"
#    - Ask: "What airlines are in the database?"
#    - See answer from PostgreSQL data via RAG!
```

## Example Queries

Once PostgreSQL data is indexed, you can ask:

**For airlines_db:**
- "What airlines operate in the USA?"
- "List all airports in California"
- "Which flights depart from JFK?"
- "Show me aircraft manufactured by Boeing"

**Combined (documents + database):**
- "What are the key stakeholders mentioned in the document, and which airlines are in the database?"
- "Compare the airlines listed in the uploaded report with the database"

## Benefits

✅ **Unified Semantic Search**: Search across documents and database with natural language
✅ **No SQL Required**: Users don't need to write SQL queries
✅ **Better Context**: LLM gets relevant data from all sources automatically
✅ **Scalable**: Add more data sources easily (e.g., API data, logs)
✅ **Consistent**: Same retrieval mechanism for all data types
✅ **Fast**: Single vector search vs. multiple API/SQL calls

## Performance Considerations

- **Chunk Size**: 5 rows per chunk works well for most tables
  - Too small (1-2): More vectors, slower search, better precision
  - Too large (10+): Fewer vectors, faster search, less precision

- **Indexing Time**: Depends on table size
  - Small tables (< 1K rows): Seconds
  - Medium tables (1K-10K): Minutes
  - Large tables (> 10K): Use `limit_per_table`

- **Re-indexing**: Schedule periodic re-indexing for frequently updated tables
  - Cron job / scheduled task
  - Trigger-based (on data changes)
  - Manual re-index as needed

## Future Enhancements

- [ ] Automatic change detection (CDC - Change Data Capture)
- [ ] Incremental indexing (only changed rows)
- [ ] Multi-table joins in text representation
- [ ] Custom text formatters per table
- [ ] Scheduled background indexing
- [ ] Index status dashboard
- [ ] Webhook triggers for re-indexing

## Troubleshooting

**Issue**: Indexing takes too long
- **Solution**: Use `limit_per_table` to index subset first
- **Solution**: Index specific high-value tables only

**Issue**: Query returns no PostgreSQL data
- **Solution**: Check if tables are indexed (look at metrics)
- **Solution**: Verify namespace is "all" or "postgresql-data"

**Issue**: Database connection errors
- **Solution**: Check PostgreSQL is running
- **Solution**: Verify credentials in `Backend/.env`

**Issue**: Out of memory during indexing
- **Solution**: Reduce chunk_size or use limit_per_table
- **Solution**: Index tables one at a time

## Summary

PostgreSQL is now fully integrated into the RAG layer! All data sources go through the same pipeline:
1. Extract data
2. Chunk into meaningful pieces
3. Embed using llama-text-embed-v2
4. Index in Pinecone
5. Query via semantic search
6. Generate answers with LLM

This is a proper RAG architecture where the vector database is the single source of truth for retrieval.
