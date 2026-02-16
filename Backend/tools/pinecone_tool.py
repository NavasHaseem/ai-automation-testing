from typing import List, Dict, Any
from langchain_openai import OpenAIEmbeddings
from langchain_core.tools import tool
from pinecone import Pinecone
from states.base_state import AgentState, RetrievedChunk
 
from dotenv import load_dotenv
import os 
load_dotenv()

embedding_model = OpenAIEmbeddings(
    model="text-embedding-3-large",
    dimensions=1024,
    openai_api_key=os.environ["OPENAI_API_KEY"],
)

# -----------------------------
# Pinecone Retrieval Tool
# -----------------------------
def pinecone_retrieval_tool(
    state: AgentState,
    top_k: int = 5,
) -> List[RetrievedChunk]:
    """
    Fetch relevant knowledge chunks from Pinecone using Jira labels and description.

    Performs semantic similarity search across Pinecone vector index to retrieve
    authoritative chunks related to a Jira story. The query is constructed from
    Jira labels and full description (including acceptance criteria).

    This tool is deterministic and does NOT use LLM reasoning.
    All returned data comes directly from Pinecone.

    Args:
        labels: List of Jira labels used as domain and namespace hints.
                Examples:
                    ["airline-api", "health-check"]
                    ["payment", "authentication"]

        description: Full Jira story description including acceptance criteria.
                     Used as the primary semantic query input.

        top_k: Number of top similar chunks to retrieve from Pinecone.
               Default: 5

    Returns:
        Success response:
        {
            "count": 3,
            "items": [
                {
                    "chunk_id": "chunk-001",
                    "text": "Health check endpoints must return HTTP 200 when service is healthy.",
                    "source": "confluence",
                    "namespace": "airline-domain",
                    "metadata": {
                        "page_id": "CONF-101",
                        "service": "flight-service"
                    },
                    "score": 0.92
                },
                {
                    "chunk_id": "chunk-045",
                    "text": "All airline backend services must expose /health endpoints.",
                    "source": "jira",
                    "namespace": "airline-domain",
                    "metadata": {
                        "story_key": "AIR-88"
                    },
                    "score": 0.87
                }
            ],
            "success": true
        }

        Error response:
        {
            "count": 0,
            "items": [],
            "success": false,
            "error": "Pinecone query failed or no relevant chunks found"
        }
 
    """

    # 1️⃣ Build query text
    query_text = " ".join(state.jira_story.labels) + " " + state.jira_story.description

    # 2️⃣ Embed query
    query_vector = embedding_model.embed_query(query_text)

    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index(os.environ["PINECONE_INDEX_NAME"])
    stats = index.describe_index_stats()
    namespaces = stats.get("namespaces", {}).keys()
    all_matches: List[Dict[str, Any]] = []

    for ns in namespaces:
        try:
            res = index.query(
                vector=query_vector,
                namespace=ns,
                top_k=top_k, 
                include_metadata=True,
            )
            print('res :', res)

            for match in res.get("matches", []):
                match["namespace"] = ns  # 🔥 keep provenance
                all_matches.append(match)
        except Exception as e:
            print(f"⚠️ Namespace '{ns}' failed: {e}")

    all_matches.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    retrieved_chunks: List[RetrievedChunk] = []

    # 4️⃣ Normalize results
    retrieved_chunks:List[Dict[str, Any]] = []
    for match in all_matches:
        metadata = match.get("metadata", {})


        retrieved_chunks.append(
            {
                "chunk_id": match.get("id"),
                "text": metadata.get("text", ""),
                "source": metadata.get("source", "unknown"),
                "namespace": metadata.get("namespace", "default"),
                "metadata": {
                    k: v
                    for k, v in metadata.items()
                    if k not in {"text", "source", "namespace"}
                },
                "score": match.get("score"),
            }
        )

    # 5️⃣ Update state (important)
    # state.retrieved_chunks = retrieved_chunks

    return {
        "retrieved_chunks": retrieved_chunks
    }