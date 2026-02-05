# utils/langgraph_agent.py
"""
LangGraph-based agentic workflow for intelligent document processing.
This agent orchestrates document analysis, chunking decisions, and semantic search.
"""
import os
from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


# Define the state for our agent workflow
class DocumentProcessingState(TypedDict):
    """State object for document processing workflow."""
    document_text: str
    filename: str
    file_id: str
    analysis: str
    chunk_strategy: str
    chunk_size: int
    chunk_overlap: int
    chunks: List[str]
    embeddings: List[List[float]]
    metadata: Dict[str, Any]
    error: str | None
    step: str


def analyze_document_node(state: DocumentProcessingState) -> DocumentProcessingState:
    """
    Analyze document to determine optimal chunking strategy.
    This node examines document characteristics like length, structure, etc.
    """
    text = state["document_text"]
    filename = state["filename"]
    
    # Simple heuristic-based analysis
    word_count = len(text.split())
    char_count = len(text)
    has_sections = "\n\n" in text or "\n#" in text
    
    analysis = f"Document: {filename}\n"
    analysis += f"Length: {word_count} words, {char_count} characters\n"
    analysis += f"Has sections: {has_sections}\n"
    
    # Determine chunk strategy
    if char_count < 1000:
        chunk_strategy = "single_chunk"
        chunk_size = char_count
        chunk_overlap = 0
    elif has_sections:
        chunk_strategy = "section_based"
        chunk_size = 1500
        chunk_overlap = 200
    else:
        chunk_strategy = "fixed_size"
        chunk_size = 1200
        chunk_overlap = 150
    
    return {
        **state,
        "analysis": analysis,
        "chunk_strategy": chunk_strategy,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "step": "analyzed"
    }


def chunk_document_node(state: DocumentProcessingState) -> DocumentProcessingState:
    """
    Chunk document based on the determined strategy.
    """
    from Backend.utils.chunking import naive_chunks
    
    text = state["document_text"]
    chunk_size = state["chunk_size"]
    chunk_overlap = state["chunk_overlap"]
    
    chunks = naive_chunks(text, chunk_chars=chunk_size, overlap=chunk_overlap)
    
    return {
        **state,
        "chunks": chunks,
        "step": "chunked"
    }


def embed_chunks_node(state: DocumentProcessingState) -> DocumentProcessingState:
    """
    Generate embeddings for document chunks.
    """
    from Backend.utils.embedding import embed_texts
    
    chunks = state["chunks"]
    
    try:
        embeddings = embed_texts(chunks)
        return {
            **state,
            "embeddings": embeddings,
            "step": "embedded"
        }
    except Exception as e:
        return {
            **state,
            "error": f"Embedding failed: {str(e)}",
            "step": "error"
        }


def should_continue_to_embed(state: DocumentProcessingState) -> str:
    """
    Routing function to determine if we should continue to embedding.
    """
    if not state.get("chunks"):
        return "error"
    return "embed"


def should_continue_after_embed(state: DocumentProcessingState) -> str:
    """
    Routing function after embedding.
    """
    if state.get("error"):
        return "error"
    return "complete"


def create_document_processing_graph():
    """
    Create the LangGraph workflow for document processing.
    
    Workflow:
    1. Analyze document → Determine chunking strategy
    2. Chunk document → Create text chunks
    3. Embed chunks → Generate vector embeddings
    """
    workflow = StateGraph(DocumentProcessingState)
    
    # Add nodes
    workflow.add_node("analyze", analyze_document_node)
    workflow.add_node("chunk", chunk_document_node)
    workflow.add_node("embed", embed_chunks_node)
    
    # Define edges
    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "chunk")
    
    # Conditional routing after chunking
    workflow.add_conditional_edges(
        "chunk",
        should_continue_to_embed,
        {
            "embed": "embed",
            "error": END
        }
    )
    
    # Conditional routing after embedding
    workflow.add_conditional_edges(
        "embed",
        should_continue_after_embed,
        {
            "complete": END,
            "error": END
        }
    )
    
    return workflow.compile()


def process_document_with_agent(
    document_text: str,
    filename: str,
    file_id: str,
    metadata: Dict[str, Any] | None = None
) -> DocumentProcessingState:
    """
    Process a document using the LangGraph agent workflow.
    
    Args:
        document_text: The text content of the document
        filename: Name of the file
        file_id: MongoDB file ID
        metadata: Optional metadata to attach
    
    Returns:
        Final state containing chunks, embeddings, and analysis
    """
    # Create the graph
    graph = create_document_processing_graph()
    
    # Initialize state
    initial_state: DocumentProcessingState = {
        "document_text": document_text,
        "filename": filename,
        "file_id": file_id,
        "analysis": "",
        "chunk_strategy": "",
        "chunk_size": 1200,
        "chunk_overlap": 150,
        "chunks": [],
        "embeddings": [],
        "metadata": metadata or {},
        "error": None,
        "step": "initialized"
    }
    
    # Run the workflow
    final_state = graph.invoke(initial_state)
    
    return final_state


# Query agent for intelligent search
class QueryState(TypedDict):
    """State for query processing workflow."""
    query_text: str
    query_embedding: List[float]
    jira_context: Dict[str, Any] | None
    filter_metadata: Dict[str, Any]
    namespace: str
    top_k: int
    results: List[Dict[str, Any]]
    step: str


def embed_query_node(state: QueryState) -> QueryState:
    """Embed the query text."""
    from Backend.utils.embedding import embed_texts
    
    query_text = state["query_text"]
    embeddings = embed_texts([query_text])
    
    return {
        **state,
        "query_embedding": embeddings[0],
        "step": "embedded"
    }


def build_filter_node(state: QueryState) -> QueryState:
    """
    Build intelligent filter based on query context and Jira data.
    """
    base_filter = {"source": {"$eq": "mongodb"}}
    
    if state.get("jira_context"):
        jira_ctx = state["jira_context"]
        # Add Jira-based filtering
        if jira_ctx.get("project"):
            base_filter["jira_project"] = {"$eq": jira_ctx["project"]}
        if jira_ctx.get("labels"):
            base_filter["jira_labels"] = {"$in": jira_ctx["labels"]}
    
    return {
        **state,
        "filter_metadata": base_filter,
        "step": "filter_built"
    }


def search_vectors_node(state: QueryState) -> QueryState:
    """Execute vector search."""
    from Backend.utils.pinecone_store import query
    
    results = query(
        vector=state["query_embedding"],
        top_k=state["top_k"],
        namespace=state["namespace"],
        filter=state["filter_metadata"]
    )
    
    matches = results.get("matches", [])
    
    return {
        **state,
        "results": matches,
        "step": "complete"
    }


def create_query_graph():
    """Create LangGraph workflow for intelligent querying."""
    workflow = StateGraph(QueryState)
    
    # Add nodes
    workflow.add_node("embed_query", embed_query_node)
    workflow.add_node("build_filter", build_filter_node)
    workflow.add_node("search", search_vectors_node)
    
    # Define edges
    workflow.set_entry_point("embed_query")
    workflow.add_edge("embed_query", "build_filter")
    workflow.add_edge("build_filter", "search")
    workflow.add_edge("search", END)
    
    return workflow.compile()


def query_with_agent(
    query_text: str,
    namespace: str = "mongodb-files",
    top_k: int = 5,
    jira_context: Dict[str, Any] | None = None
) -> List[Dict[str, Any]]:
    """
    Execute intelligent query using LangGraph agent.
    
    Args:
        query_text: The search query
        namespace: Pinecone namespace
        top_k: Number of results
        jira_context: Optional Jira context for filtering
    
    Returns:
        List of matching results with metadata
    """
    graph = create_query_graph()
    
    initial_state: QueryState = {
        "query_text": query_text,
        "query_embedding": [],
        "jira_context": jira_context,
        "filter_metadata": {},
        "namespace": namespace,
        "top_k": top_k,
        "results": [],
        "step": "initialized"
    }
    
    final_state = graph.invoke(initial_state)
    return final_state["results"]
