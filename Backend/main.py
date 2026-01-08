
# backend/main.py
import os
from typing import Annotated

from fastapi import Request, Header
from bson import ObjectId
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.models import Response
from fastapi.responses import JSONResponse
from gridfs import NoFile

from dotenv import load_dotenv, find_dotenv
from pymongo.errors import ServerSelectionTimeoutError
from bson import ObjectId, errors as bson_errors
from fastapi.responses import Response as StarletteRespons

load_dotenv(find_dotenv())

# ---- Optional simple token auth ----
def get_token_dependency():
    expected = os.getenv("API_AUTH_TOKEN")
    def verify(token: str = Form(None)):
        if expected and token != expected:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return True
    return verify
def get_token(authorization: str = Header(None)):
    expected = os.getenv("API_AUTH_TOKEN")
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.removeprefix("Bearer ").strip()
    if token !=expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

# ---- Import service helpers ----
from utils.MangoDB import upload_file, list_files, download_file, delete_file
from utils.parse_text import extract_text, ParseError
from utils.embedding import embed_texts, get_model_info
from utils.pinecone_store import ensure_index, upsert_chunks, query
from Models.Model import ListQuery, EmbedUpsertRequest, QueryRequest, UpsertResponse, QueryResponse, QueryMatch, JiraStory, JiraStoriesResponse, PostgresTableListResponse, PostgresQueryRequest, PostgresQueryResponse, PostgresIndexRequest, PostgresIndexResponse

app = FastAPI(title="AI Testing Backend", version="1.0.0")

# ---- CORS for Streamlit (localhost:8501) ----
origins = [
    "http://localhost:8501",
    "http://127.0.0.1:8501",
    os.getenv("FRONTEND_ORIGIN", ""),
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in origins if o],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ---- Health ----
@app.get("/health")
def health():
    return {"status": "ok"}

# ---- Upload to MongoDB ----

# backend/main.py
@app.post("/files/upload")
async def upload_endpoint(
    file: UploadFile = File(...),
    tags: str = Form(""),
    notes: str = Form(""),
    _auth: bool = Depends(get_token_dependency())  # optional auth
):
    data = await file.read()
    metadata = {
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "notes": notes.strip(),
        "content_type": file.content_type,
    }
    file_id = upload_file(data, file.filename, metadata)  # <- must return str id
    return {"file_id": file_id}


# ---- List files ----
@app.post("/files/list")
def list_endpoint(body: ListQuery):
    files = list_files(body.name_contains, body.tag_contains, body.limit)
    return {"files": files}

# ---- Delete file ----
@app.delete("/files/{file_id}")
def delete_endpoint(file_id: str, _auth: bool = Depends(get_token_dependency())):
    delete_file(file_id)
    return {"deleted": file_id}

@app.get("/files/download/{file_id}")
def get_file(file_id: str,_auth: bool = Depends(get_token_dependency())):
    try:
        ObjectId(file_id)
    except bson_errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid file id")

    try:
        data, info = download_file(file_id)
    except NoFile:
        raise HTTPException(status_code=404, detail="File not found")
    except ServerSelectionTimeoutError:
        raise HTTPException(status_code=503, detail="Storage unavailable")
    except Exception as e:
        # If you want to map all errors to 404 as in your snippet, you can:
        # raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    filename = info.get("filename") or file_id
    metadata = info.get("metadata", {}) or {}
    content_type = metadata.get("contentType", "application/octet-stream")
    length = info.get("length", len(data))

    headers = {
        "Content-Length": str(length),  # ✅ str values are fine for Starlette Response
        "Content-Disposition": f'attachment; filename="{filename}"; filename*=UTF-8\'\'{filename}',
    }

    # ✅ Return the correct HTTP response type
    return StarletteRespons(content=data, media_type=content_type, headers=headers)


# ---- Embed + Upsert to Pinecone using LangGraph Agent ----
@app.post("/pinecone/embed-upsert", response_model=UpsertResponse)
async def embed_upsert_endpoint(req:EmbedUpsertRequest, _auth: bool = Depends(get_token)):
    from utils.langgraph_agent import process_document_with_agent

    content, info = download_file(req.file_id)
    # Parse text
    try:
        text = extract_text(info["filename"], content)
    except ParseError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Use LangGraph agent to process document intelligently
    agent_state = process_document_with_agent(
        document_text=text,
        filename=info["filename"],
        file_id=req.file_id,
        metadata=req.metadata
    )
    
    # Check for errors
    if agent_state.get("error"):
        raise HTTPException(status_code=500, detail=agent_state["error"])
    
    chunks = agent_state["chunks"]
    vectors = agent_state["embeddings"]
    
    if not chunks or not vectors:
        raise HTTPException(status_code=400, detail="No chunks or embeddings produced.")

    # Get model info
    model_name, dim = get_model_info()
    
    # Ensure index (matching dimension)
    ensure_index(dimension=len(vectors[0]))

    # Build payload
    ts = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    payload = []
    for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
        md = {
            "file_id": req.file_id,
            "filename": info["filename"],
            "chunk_id": i,
            "text": chunk,  # Store full chunk text
            "text_preview": chunk[:300],  # Keep preview for display
            "uploaded_at": ts,
            "source": "mongodb",
            "chunk_strategy": agent_state["chunk_strategy"],  # Agent's decision
        }
        if req.metadata:
            md.update(req.metadata)
        payload.append((f"{req.file_id}-{i}", vec, md))

    # Upsert
    n = upsert_chunks(payload, namespace=req.namespace)
    # Return count, model info, and agent analysis
    return UpsertResponse(
        status="success",
        vectors_upserted=n,
        model=model_name,
        dimension=dim,
        chunk_strategy=agent_state["chunk_strategy"],
        analysis=agent_state["analysis"]
    )




@app.post("/pinecone/query", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest, _auth: bool = Depends(get_token)):
    from utils.embedding import embed_texts
    from utils.pinecone_store import query as pinecone_query
    from openai import AzureOpenAI
    
    # Embed the query
    qvec = embed_texts([req.text])[0]
    
    # Query Pinecone - this now includes BOTH documents and PostgreSQL data
    # Documents are in namespace "mongodb-files"
    # PostgreSQL data is in namespace "postgresql-data"
    
    all_matches = []
    
    # Search in document namespace
    if req.namespace == "mongodb-files" or req.namespace == "all":
        doc_result = pinecone_query(
            vector=qvec,
            top_k=req.top_k,
            namespace="mongodb-files",
            filter=req.filter or {}
        )
        all_matches.extend(doc_result.get("matches", []))
    
    # Search in PostgreSQL namespace (RAG layer)
    if req.namespace == "postgresql-data" or req.namespace == "all":
        pg_result = pinecone_query(
            vector=qvec,
            top_k=req.top_k,
            namespace="postgresql-data",
            filter={"source": {"$eq": "postgresql"}}
        )
        all_matches.extend(pg_result.get("matches", []))
    
    # If namespace is not specified as "all", use the provided namespace
    if req.namespace not in ["mongodb-files", "postgresql-data", "all"]:
        result = pinecone_query(
            vector=qvec,
            top_k=req.top_k,
            namespace=req.namespace,
            filter=req.filter or {}
        )
        all_matches = result.get("matches", [])
    
    # Sort by score and limit to top_k
    all_matches.sort(key=lambda x: x.get("score", 0), reverse=True)
    all_matches = all_matches[:req.top_k * 2]  # Get more for better context
    
    # Convert matches to QueryMatch models
    matches = [
        QueryMatch(
            id=match["id"],
            score=match["score"],
            metadata=match.get("metadata", {})
        )
        for match in all_matches
    ]
    
    # Generate contextual answer using LLM with context from Pinecone (unified RAG)
    answer = "No relevant information found."
    
    # Combine contexts from all sources retrieved from Pinecone
    all_contexts = []
    postgres_data = None
    
    # Separate document and database contexts
    doc_contexts = []
    db_contexts = []
    
    for i, match in enumerate(matches[:10], 1):
        full_text = match.metadata.get("text", "") or match.metadata.get("text_preview", "")
        source = match.metadata.get("source", "unknown")
        
        if source == "postgresql":
            db_contexts.append(f"Database Record {len(db_contexts)+1}: {full_text}")
        else:
            doc_contexts.append(f"Document {len(doc_contexts)+1}: {full_text}")
    
    # Add document context
    if doc_contexts:
        all_contexts.append("=== Document Context (from uploaded files) ===")
        all_contexts.extend(doc_contexts)
    
    # Add PostgreSQL context (from Pinecone RAG layer)
    if db_contexts:
        all_contexts.append("\n=== Database Context (from PostgreSQL via RAG) ===")
        all_contexts.extend(db_contexts)
        postgres_data = {
            "source": "pinecone_rag",
            "record_count": len(db_contexts),
            "message": "Retrieved from Pinecone vector database (PostgreSQL data indexed)"
        }
    
    if all_contexts:
        combined_context = "\n\n".join(all_contexts)
        
        # Call Azure OpenAI to generate answer
        try:
            client = AzureOpenAI(
                api_key=os.getenv("API_KEY"),
                api_version=os.getenv("API_VERSION"),
                azure_endpoint=os.getenv("API_BASE")
            )
            
            response = client.chat.completions.create(
                model=os.getenv("ENGINE", "gpt-4-32k"),
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided context from multiple sources (documents and database). All data has been retrieved through semantic search. Synthesize information from all sources to provide a comprehensive answer."},
                    {"role": "user", "content": f"Context from semantic search:\n{combined_context}\n\nQuestion: {req.text}\n\nProvide a clear, comprehensive answer based on the context above."}
                ],
                temperature=0.3,
                max_tokens=800
            )
            answer = response.choices[0].message.content
        except Exception as e:
            answer = f"Error generating answer: {str(e)}"
    
    return QueryResponse(
        status="success",
        matches=matches,
        total_results=len(matches),
        answer=answer,
        postgres_data=postgres_data
    )


# ---- Jira Integration ----
@app.get("/jira/stories", response_model=JiraStoriesResponse)
async def get_jira_stories(max_results: int = 100, _auth: bool = Depends(get_token)):
    """
    Fetch all stories from Jira
    """
    from utils.jira_api import search_jql
    
    try:
        # JQL to get all stories (issue type = Story)
        jql = "issuetype = Story ORDER BY created DESC"
        
        result = search_jql(
            jql=jql,
            fields=["summary", "status", "issuetype", "assignee", "priority"],
            max_results=max_results
        )
        
        # Parse the issues
        stories = []
        for issue in result.get("issues", []):
            fields = issue.get("fields", {})
            assignee_name = None
            if fields.get("assignee"):
                assignee_name = fields["assignee"].get("displayName")
            
            priority_name = None
            if fields.get("priority"):
                priority_name = fields["priority"].get("name")
            
            stories.append(JiraStory(
                key=issue.get("key", ""),
                summary=fields.get("summary", ""),
                status=fields.get("status", {}).get("name", ""),
                issue_type=fields.get("issuetype", {}).get("name", ""),
                assignee=assignee_name,
                priority=priority_name
            ))
        
        return JiraStoriesResponse(
            status="success",
            total=result.get("total", 0),
            stories=stories
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Jira API error: {str(e)}")


# ---- PostgreSQL Integration ----
@app.get("/postgres/tables", response_model=PostgresTableListResponse)
async def get_postgres_tables(_auth: bool = Depends(get_token)):
    """
    Get list of all tables in PostgreSQL database
    """
    from utils.postgres import get_tables
    
    try:
        tables = get_tables()
        return PostgresTableListResponse(
            status="success",
            tables=tables
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PostgreSQL error: {str(e)}")

@app.post("/postgres/query", response_model=PostgresQueryResponse)
async def query_postgres(req: PostgresQueryRequest, _auth: bool = Depends(get_token)):
    """
    Query PostgreSQL database - either by table name or custom SQL
    """
    from utils.postgres import get_table_data, execute_custom_query
    
    try:
        if req.custom_query:
            # Execute custom SQL query
            data = execute_custom_query(req.custom_query)
        elif req.table_name:
            # Get data from specific table
            data = get_table_data(req.table_name, req.limit)
        else:
            raise HTTPException(status_code=400, detail="Either table_name or custom_query must be provided")
        
        return PostgresQueryResponse(
            status="success",
            data=data,
            row_count=len(data)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PostgreSQL error: {str(e)}")


# ---- PostgreSQL RAG Indexing ----
@app.post("/postgres/index", response_model=PostgresIndexResponse)
async def index_postgres_to_pinecone(req: PostgresIndexRequest, _auth: bool = Depends(get_token)):
    """
    Index PostgreSQL tables into Pinecone for RAG.
    Extracts data, chunks it, embeds it, and stores in Pinecone vector DB.
    """
    from utils.postgres_indexer import index_table_to_pinecone, index_all_tables_to_pinecone
    
    try:
        if req.table_name:
            # Index a specific table
            result = index_table_to_pinecone(
                table_name=req.table_name,
                namespace=req.namespace,
                chunk_size=req.chunk_size,
                limit=req.limit_per_table
            )
            
            # Format as overall response
            if result['status'] == 'success':
                return PostgresIndexResponse(
                    status="success",
                    tables_processed=1,
                    total_rows=result['rows_processed'],
                    total_chunks=result['chunks_created'],
                    total_vectors=result['vectors_upserted'],
                    namespace=req.namespace,
                    table_results=[result]
                )
            else:
                raise HTTPException(status_code=500, detail=result.get('error', 'Unknown error'))
        else:
            # Index all tables
            result = index_all_tables_to_pinecone(
                namespace=req.namespace,
                chunk_size=req.chunk_size,
                limit_per_table=req.limit_per_table,
                exclude_tables=req.exclude_tables
            )
            
            if result['status'] == 'success':
                return PostgresIndexResponse(
                    status="success",
                    tables_processed=result['tables_processed'],
                    total_rows=result['total_rows'],
                    total_chunks=result['total_chunks'],
                    total_vectors=result['total_vectors'],
                    namespace=result['namespace'],
                    table_results=result.get('table_results')
                )
            else:
                raise HTTPException(status_code=500, detail=result.get('error', 'Unknown error'))
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing error: {str(e)}")
