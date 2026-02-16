
# utils/embedding.py
import os
import requests
from typing import List, Tuple



def get_model_info() -> Tuple[str, int]:

    model = os.getenv("PINECONE_EMBED_MODEL", "llama-text-embed-v2")
    try:
        dim = int(os.getenv("PINECONE_EMBED_DIM", "1024"))
    except ValueError:
        dim = 1024
    return model, dim


def embed_texts(texts: List[str]) -> List[List[float]]:

    if not texts:
        return []

    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise RuntimeError("PINECONE_API_KEY not set")

    model, dim = get_model_info()
    api_ver = os.getenv("PINECONE_API_VERSION", "2025-10")  # recent version supporting inference

    headers = {
        "Api-Key": api_key,
        "Content-Type": "application/json",
        "X-Pinecone-API-Version": api_ver,
    }


    payload = {
        "model": model,
        "parameters": {
            "input_type": "passage",
            "truncate": "END",

            "dimension": dim
        },
        "inputs": [{"text": t} for t in texts],
    }

    r = requests.post("https://api.pinecone.io/embed", headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json().get("data", [])
    vectors = [row["values"] for row in data]

    # Sanity check
    if not vectors:
        raise RuntimeError("No embeddings returned from Pinecone Inference")
    actual_dim = len(vectors[0])
    if actual_dim != dim:
        raise RuntimeError(
            f"Embedding dimension mismatch: requested {dim}, got {actual_dim}. "
            f"Ensure X-Pinecone-API-Version is >= 2025-04 for custom dimensions."
        )
    return vectors
