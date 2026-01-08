
# utils/postgres_rag.py
import os
from typing import List, Dict, Any
from utils.postgres import execute_query, get_tables
from openai import AzureOpenAI

def generate_sql_from_query(user_query: str, available_tables: List[str]) -> str:
    """
    Use LLM to generate SQL query from natural language
    """
    client = AzureOpenAI(
        api_key=os.getenv("API_KEY"),
        api_version=os.getenv("API_VERSION"),
        azure_endpoint=os.getenv("API_BASE")
    )
    
    tables_info = ", ".join(available_tables)
    
    prompt = f"""You are a PostgreSQL expert. Generate a SELECT query based on the user's question.

Available tables: {tables_info}

User question: {user_query}

Rules:
1. Only generate SELECT queries
2. Use LIMIT 10 for safety
3. If the question doesn't relate to the available tables, return "NO_QUERY"
4. Return ONLY the SQL query, no explanation

SQL Query:"""

    try:
        response = client.chat.completions.create(
            model=os.getenv("ENGINE", "gpt-4-32k"),
            messages=[
                {"role": "system", "content": "You are a PostgreSQL expert that generates safe SELECT queries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=200
        )
        
        sql = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if sql.startswith("```"):
            sql = sql.split("```")[1]
            if sql.startswith("sql"):
                sql = sql[3:]
            sql = sql.strip()
        
        return sql if sql != "NO_QUERY" else None
        
    except Exception as e:
        print(f"Error generating SQL: {e}")
        return None


def get_postgres_context(user_query: str) -> Dict[str, Any]:
    """
    Get relevant PostgreSQL data for RAG based on user query
    Returns formatted context and metadata
    """
    try:
        # Get available tables
        tables = get_tables()
        
        if not tables:
            return {"context": "", "sql": None, "rows": 0, "error": "No tables found"}
        
        # Generate SQL from natural language query
        sql = generate_sql_from_query(user_query, tables)
        
        if not sql:
            return {"context": "", "sql": None, "rows": 0, "error": "No relevant SQL query generated"}
        
        # Execute the query
        results = execute_query(sql)
        
        if not results:
            return {"context": "", "sql": sql, "rows": 0, "error": "Query returned no results"}
        
        # Format results as context for LLM
        context_parts = []
        context_parts.append(f"PostgreSQL Query Results (from query: {sql}):")
        context_parts.append("-" * 80)
        
        # Format as table
        if results:
            # Get column names
            columns = list(results[0].keys())
            
            # Add header
            context_parts.append(" | ".join(columns))
            context_parts.append("-" * 80)
            
            # Add rows (limit to first 10 for context)
            for row in results[:10]:
                values = [str(row.get(col, "")) for col in columns]
                context_parts.append(" | ".join(values))
        
        context = "\n".join(context_parts)
        
        return {
            "context": context,
            "sql": sql,
            "rows": len(results),
            "data": results,
            "error": None
        }
        
    except Exception as e:
        return {"context": "", "sql": None, "rows": 0, "error": str(e)}
