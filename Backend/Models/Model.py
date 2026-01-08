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
    namespace: str = "all"  # Can be "mongodb-files", "postgresql-data", or "all" to search both
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
    postgres_data: Optional[Dict[str, Any]] = None  # PostgreSQL context
    postgres_data: Optional[Dict[str, Any]] = None  # PostgreSQL context

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

class PostgresTableListResponse(BaseModel):
    status: str
    tables: List[str]

class PostgresQueryRequest(BaseModel):
    table_name: Optional[str] = None
    custom_query: Optional[str] = None
    limit: int = 100

class PostgresQueryResponse(BaseModel):
    status: str
    data: List[Dict[str, Any]]
    row_count: int

class PostgresIndexRequest(BaseModel):
    table_name: Optional[str] = None  # Specific table or None for all tables
    namespace: str = "postgresql-data"
    chunk_size: int = 5  # Number of rows per chunk
    limit_per_table: Optional[int] = None  # Limit rows per table
    exclude_tables: Optional[List[str]] = None  # Tables to skip

class PostgresIndexResponse(BaseModel):
    status: str
    tables_processed: int
    total_rows: int
    total_chunks: int
    total_vectors: int
    namespace: str
    table_results: Optional[List[Dict[str, Any]]] = None
