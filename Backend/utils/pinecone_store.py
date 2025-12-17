
import os
from typing import List, Dict, Any, Tuple
from pinecone import Pinecone, ServerlessSpec



PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX")
CLOUD = os.getenv("PINECONE_CLOUD", "aws")
REGION = os.getenv("PINECONE_REGION", "us-east-1")

_pc: Pinecone | None = None

def _get_pc() -> Pinecone:
    global _pc
    if _pc is None:
        if not PINECONE_API_KEY:
            raise RuntimeError("PINECONE_API_KEY not set")
        _pc = Pinecone(api_key=PINECONE_API_KEY)
    return _pc


def ensure_index(dimension: int, metric: str = "cosine") -> None:
    """
    Create the index if missing; verify dimension if it exists.
    Raises with a clear error if dimension mismatches (so you can recreate intentionally).
    """
    pc = _get_pc()
    names = [i.name for i in pc.list_indexes()]
    if INDEX_NAME not in names:
        pc.create_index(
            name=INDEX_NAME,
            dimension=dimension,
            metric=metric,
            spec=ServerlessSpec(cloud=CLOUD, region=REGION),
        )
        return

    # Verify dimension if index already exists
    desc = pc.describe_index(INDEX_NAME)
    idx_dim = getattr(desc, "dimension", None)
    if idx_dim and idx_dim != dimension:
        raise ValueError(
            f"Pinecone index '{INDEX_NAME}' exists with dimension {idx_dim}, "
            f"but app expects {dimension}. Recreate the index to match."
        )

#
# def upsert_chunks(vectors: List[Tuple[str, List[float], Dict[str, Any]]], namespace: str = "default") -> int:
#
#     if not vectors:
#         return 0
#
#
#     dim = len(vectors[0][1])
#     for _, vals, _ in vectors:
#         if len(vals) != dim:
#             raise ValueError("All vectors must have the same dimension")
#
#
#     ensure_index(dimension=dim)
#
#     pc = _get_pc()
#     index = pc.Index(INDEX_NAME)
#     payload = [{"id": vid, "values": vals, "metadata": md} for vid, vals, md in vectors]
#     res = index.upsert(vectors=payload, namespace=namespace)
#
#     return res.get("upsertedCount", 0)


def upsert_chunks(vectors, namespace="default") -> int:
    pc = _get_pc()
    index = pc.Index(INDEX_NAME)
    payload = [{"id": vid, "values": vals, "metadata": md} for vid, vals, md in vectors]
    res = index.upsert(vectors=payload, namespace=namespace)
    # Pinecone SDK may not return upsertedCount reliably; fallback to len(payload)
    return len(payload)



def query(vector: List[float], top_k: int = 5, namespace: str = "default", filter: Dict[str, Any] | None = None):

    pc = _get_pc()
    index = pc.Index(INDEX_NAME)
    return index.query(
        vector=vector,
        top_k=top_k,
        include_metadata=True,
        namespace=namespace,
        filter=filter or {},
    )
