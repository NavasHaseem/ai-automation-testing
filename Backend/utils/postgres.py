
# utils/postgres.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any

def get_connection():
    """Create and return a PostgreSQL database connection"""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )

def execute_query(query: str, params: tuple = None) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query and return results as list of dictionaries
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()
            return [dict(row) for row in results]
    finally:
        conn.close()

def get_tables() -> List[str]:
    """
    Get list of all tables in the database
    """
    query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """
    results = execute_query(query)
    return [row['table_name'] for row in results]

def get_table_data(table_name: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get data from a specific table
    """
    # Using parameterized query for table name is not supported,
    # so we validate the table name first
    tables = get_tables()
    if table_name not in tables:
        raise ValueError(f"Table '{table_name}' not found")
    
    query = f"SELECT * FROM {table_name} LIMIT %s"
    return execute_query(query, (limit,))

def execute_custom_query(sql: str) -> List[Dict[str, Any]]:
    """
    Execute a custom SQL query (read-only)
    """
    # Basic safety check - only allow SELECT queries
    if not sql.strip().upper().startswith('SELECT'):
        raise ValueError("Only SELECT queries are allowed")
    
    return execute_query(sql)
