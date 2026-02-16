"""
PostgreSQL to Pinecone RAG Indexing Pipeline

Extracts data from PostgreSQL tables, chunks it, embeds it, and indexes in Pinecone.
This enables semantic search across structured database data.
"""

import os
from typing import List, Dict, Any, Optional
from utils.postgres import execute_query, get_tables
from utils.embedding import embed_texts
from utils.pinecone_store import upsert_chunks
from datetime import datetime, timezone
import json


def table_row_to_text(row: Dict[str, Any], table_name: str) -> str:
    """
    Convert a database row to a text representation for embedding.
    
    Args:
        row: Dictionary representing a database row
        table_name: Name of the source table
        
    Returns:
        Text representation of the row
    """
    parts = [f"Table: {table_name}"]
    
    for key, value in row.items():
        if value is not None:
            # Format based on type
            if isinstance(value, (int, float)):
                parts.append(f"{key}: {value}")
            elif isinstance(value, str):
                parts.append(f"{key}: {value}")
            elif isinstance(value, (datetime,)):
                parts.append(f"{key}: {value.isoformat()}")
            else:
                parts.append(f"{key}: {str(value)}")
    
    return "\n".join(parts)


def chunk_table_data(rows: List[Dict[str, Any]], table_name: str, chunk_size: int = 5) -> List[Dict[str, Any]]:
    """
    Chunk table rows into groups for embedding.
    For structured data, we group multiple rows together.
    
    Args:
        rows: List of database rows
        table_name: Name of the source table
        chunk_size: Number of rows per chunk
        
    Returns:
        List of chunks with text and metadata
    """
    chunks = []
    
    for i in range(0, len(rows), chunk_size):
        chunk_rows = rows[i:i + chunk_size]
        
        # Convert rows to text
        text_parts = []
        row_ids = []
        
        for row in chunk_rows:
            text_parts.append(table_row_to_text(row, table_name))
            # Try to get a primary key or use row index
            row_id = row.get('id') or row.get('_id') or i
            row_ids.append(str(row_id))
        
        chunk_text = "\n\n".join(text_parts)
        
        chunks.append({
            'text': chunk_text,
            'metadata': {
                'source': 'postgresql',
                'table_name': table_name,
                'row_ids': row_ids,
                'row_count': len(chunk_rows),
                'indexed_at': datetime.now(timezone.utc).isoformat()
            }
        })
    
    return chunks


def index_table_to_pinecone(
    table_name: str,
    namespace: str = "postgresql-data",
    chunk_size: int = 5,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Index a PostgreSQL table into Pinecone.
    
    Args:
        table_name: Name of the table to index
        namespace: Pinecone namespace to use
        chunk_size: Number of rows per chunk
        limit: Optional limit on number of rows to index
        
    Returns:
        Dictionary with indexing results
    """
    try:
        # Query the table
        query = f"SELECT * FROM {table_name}"
        if limit:
            query += f" LIMIT {limit}"
        
        rows = execute_query(query)
        
        if not rows:
            return {
                'status': 'success',
                'table_name': table_name,
                'rows_processed': 0,
                'chunks_created': 0,
                'vectors_upserted': 0,
                'message': 'No data found in table'
            }
        
        # Chunk the data
        chunks = chunk_table_data(rows, table_name, chunk_size)
        
        # Extract text for embedding
        texts = [chunk['text'] for chunk in chunks]
        
        # Generate embeddings
        embeddings = embed_texts(texts)
        
        # Prepare payload for Pinecone
        payload = []
        ts = datetime.now(timezone.utc).isoformat()
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vector_id = f"pg_{table_name}_{i}_{ts.replace(':', '-')}"
            metadata = {
                **chunk['metadata'],
                'text': chunk['text'],  # Store full text
                'text_preview': chunk['text'][:300],  # Preview for display
            }
            payload.append((vector_id, embedding, metadata))
        
        # Upsert to Pinecone
        vectors_upserted = upsert_chunks(payload, namespace=namespace)
        
        return {
            'status': 'success',
            'table_name': table_name,
            'rows_processed': len(rows),
            'chunks_created': len(chunks),
            'vectors_upserted': vectors_upserted,
            'namespace': namespace,
            'message': f'Successfully indexed {len(rows)} rows into {vectors_upserted} vectors'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'table_name': table_name,
            'error': str(e)
        }


def index_all_tables_to_pinecone(
    namespace: str = "postgresql-data",
    chunk_size: int = 5,
    limit_per_table: Optional[int] = None,
    exclude_tables: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Index all PostgreSQL tables into Pinecone.
    
    Args:
        namespace: Pinecone namespace to use
        chunk_size: Number of rows per chunk
        limit_per_table: Optional limit on rows per table
        exclude_tables: List of table names to skip
        
    Returns:
        Dictionary with overall indexing results
    """
    try:
        # Get all tables
        tables = get_tables()
        
        if not tables:
            return {
                'status': 'error',
                'message': 'No tables found in database'
            }
        
        # Filter excluded tables
        if exclude_tables:
            tables = [t for t in tables if t not in exclude_tables]
        
        results = []
        total_rows = 0
        total_chunks = 0
        total_vectors = 0
        
        for table in tables:
            print(f"Indexing table: {table}")
            result = index_table_to_pinecone(
                table_name=table,
                namespace=namespace,
                chunk_size=chunk_size,
                limit=limit_per_table
            )
            results.append(result)
            
            if result['status'] == 'success':
                total_rows += result.get('rows_processed', 0)
                total_chunks += result.get('chunks_created', 0)
                total_vectors += result.get('vectors_upserted', 0)
        
        return {
            'status': 'success',
            'tables_processed': len(results),
            'total_rows': total_rows,
            'total_chunks': total_chunks,
            'total_vectors': total_vectors,
            'namespace': namespace,
            'table_results': results
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


def search_postgres_data_in_pinecone(
    query_text: str,
    namespace: str = "postgresql-data",
    top_k: int = 5,
    table_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search PostgreSQL data that was indexed in Pinecone.
    
    Args:
        query_text: The search query
        namespace: Pinecone namespace to search
        top_k: Number of results to return
        table_filter: Optional table name to filter results
        
    Returns:
        List of matching results with metadata
    """
    from utils.pinecone_store import query as pinecone_query
    
    # Embed the query
    query_vector = embed_texts([query_text])[0]
    
    # Build filter
    filter_dict = {"source": {"$eq": "postgresql"}}
    if table_filter:
        filter_dict["table_name"] = {"$eq": table_filter}
    
    # Query Pinecone
    result = pinecone_query(
        vector=query_vector,
        top_k=top_k,
        namespace=namespace,
        filter=filter_dict
    )
    
    return result.get("matches", [])
