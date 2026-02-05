
# storage.py
import os
from typing import Optional, List, Dict, Any, Tuple
from pymongo import MongoClient
from gridfs import GridFS
from bson import ObjectId
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "filesdb")

_client: Optional[MongoClient] = None
_fs: Optional[GridFS] = None

def get_client() -> MongoClient:
    global _client
    if _client is None:
        if not MONGODB_URI:
            raise RuntimeError("MONGODB_URI not set in environment.")
        _client = MongoClient(MONGODB_URI)
    return _client

def get_fs() -> GridFS:
    global _fs
    if _fs is None:
        db = get_client()[MONGODB_DB]
        _fs = GridFS(db)
    return _fs

def upload_file(
    data: bytes,
    filename: str,
    content_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:

    fs = get_fs()
    md = metadata.copy() if metadata else {}
    if content_type:
        md["content_type"] = content_type
    file_id = fs.put(data, filename=filename, **({"metadata": md} if md else {}))
    return str(file_id)

def list_files(
    name_contains: Optional[str] = None,
    tag_contains: Optional[str] = None,
    limit: int = 100,
    sort_desc: bool = True,
) -> List[Dict[str, Any]]:

    db = get_client()[MONGODB_DB]
    files_col = db["fs.files"]
    query: Dict[str, Any] = {}
    if name_contains:
        query["filename"] = {"$regex": name_contains, "$options": "i"}
    if tag_contains:

        query["metadata.tags"] = {"$elemMatch": {"$regex": tag_contains, "$options": "i"}}

    cursor = files_col.find(query).sort("uploadDate", -1 if sort_desc else 1).limit(limit)
    out: List[Dict[str, Any]] = []
    for f in cursor:
        out.append({
            "_id": str(f["_id"]),
            "filename": f.get("filename"),
            "length": f.get("length"),
            "uploadDate": f.get("uploadDate"),
            "metadata": f.get("metadata", {}),
        })
    return out

def download_file(file_id: str) -> Tuple[bytes, Dict[str, Any]]:

    fs = get_fs()
    oid = ObjectId(file_id)
    grid_out = fs.get(oid)
    data = grid_out.read()
    info = {
        "_id": file_id,
        "filename": grid_out.filename,
        "length": grid_out.length,
        "uploadDate": grid_out.upload_date,
        "metadata": getattr(grid_out, "metadata", {}) or {},
    }
    return data, info

def delete_file(file_id: str) -> None:
    fs = get_fs()
    fs.delete(ObjectId(file_id))

