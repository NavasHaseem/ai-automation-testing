"""
Visualize LangGraph workflows.
Run this script to generate visual representations of the agent graphs.
"""

from langgraph_agent import create_document_processing_graph, create_query_graph


def visualize_graphs():
    """Generate visualizations of both agent workflows."""
    
    # Document processing graph
    doc_graph = create_document_processing_graph()
    print("Document Processing Graph:")
    print("=" * 60)
    try:
        # Try to get Mermaid representation if available
        mermaid = doc_graph.get_graph().draw_mermaid()
        print(mermaid)
    except:
        print("Graph created successfully (visualization requires graphviz)")
    
    print("\n" + "=" * 60)
    print("\nQuery Processing Graph:")
    print("=" * 60)
    
    # Query graph
    query_graph = create_query_graph()
    try:
        mermaid = query_graph.get_graph().draw_mermaid()
        print(mermaid)
    except:
        print("Graph created successfully (visualization requires graphviz)")
    
    print("\n" + "=" * 60)
    print("\n✅ LangGraph workflows are ready!")
    print("\nDocument Processing Steps:")
    print("  1. Analyze → Examines document characteristics")
    print("  2. Chunk → Applies optimal chunking strategy")
    print("  3. Embed → Generates vector embeddings")
    
    print("\nQuery Processing Steps:")
    print("  1. Embed Query → Converts text to vector")
    print("  2. Build Filter → Creates intelligent metadata filters")
    print("  3. Search → Executes vector similarity search")


if __name__ == "__main__":
    visualize_graphs()
