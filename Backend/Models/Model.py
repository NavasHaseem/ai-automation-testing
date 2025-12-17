from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class ListQuery(BaseModel):
    name_contains: Optional[str] = None
    tag_contains: Optional[str] = None
    limit: int = 100

class EmbedUpsertRequest(BaseModel):
    file_id: str
    chunk_chars: int = 1200
    chunk_overlap: int = 150
    namespace: str = "mongodb-files"
    metadata: Optional[Dict[str, Any]] = None

class UpsertResponse(BaseModel):
    status: str
    vectors_upserted: int
    model: str
    dimension: int
    chunk_strategy: str
    analysis: str

class QueryRequest(BaseModel):
    namespace: str = "mongodb-files"
    top_k: int = 5
    filter: Optional[Dict[str, Any]] = None
    text: str

class QueryMatch(BaseModel):
    id: str
    score: float
    metadata: Dict[str, Any]

class QueryResponse(BaseModel):
    status: str
    matches: List[QueryMatch]
    total_results: int
    answer: str  # LLM-generated contextual answer

class JiraStory(BaseModel):
    key: str
    summary: str
    status: str
    issue_type: str
    assignee: Optional[str] = None
    priority: Optional[str] = None

class JiraStoriesResponse(BaseModel):
    status: str
    total: int
    stories: List[JiraStory]
