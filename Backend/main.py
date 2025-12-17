
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
from Models.Model import ListQuery, EmbedUpsertRequest, QueryRequest, UpsertResponse, QueryResponse, QueryMatch, JiraStory, JiraStoriesResponse

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
    
    # Query Pinecone
    result = pinecone_query(
        vector=qvec,
        top_k=req.top_k,
        namespace=req.namespace,
        filter=req.filter or {}
    )
    
    # Convert matches to QueryMatch models
    matches = [
        QueryMatch(
            id=match["id"],
            score=match["score"],
            metadata=match.get("metadata", {})
        )
        for match in result.get("matches", [])
    ]
    
    # Generate contextual answer using LLM
    answer = "No relevant information found."
    if matches:
        # Gather context from top matches
        context_parts = []
        for match in matches[:5]:  # Use top 5 matches
            # Use full text if available, fall back to preview
            full_text = match.metadata.get("text", "") or match.metadata.get("text_preview", "")
            if full_text:
                context_parts.append(full_text)
        
        if context_parts:
            context = "\n\n".join(context_parts)
            
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
                        {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided context. If the context doesn't contain enough information, say so."},
                        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {req.text}\n\nProvide a clear, concise answer based on the context above."}
                    ],
                    temperature=0.3,
                    max_tokens=500
                )
                answer = response.choices[0].message.content
            except Exception as e:
                answer = f"Error generating answer: {str(e)}"
    
    return QueryResponse(
        status="success",
        matches=matches,
        total_results=len(matches),
        answer=answer
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
