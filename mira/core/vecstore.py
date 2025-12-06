# -*- coding: utf-8 -*-
"""Optional vector store wrapper (Chroma).

If chromadb is not installed, AVAILABLE=False and functions are no-ops.
"""
from __future__ import annotations
from typing import List, Tuple, Dict, Any

try:
    import chromadb  # type: ignore
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction  # type: ignore
    AVAILABLE = True
except Exception:
    AVAILABLE = False
    chromadb = None  # type: ignore

_client = None
_collection = None

def _ensure() -> None:
    global _client, _collection
    if not AVAILABLE:
        return
    if _client is None:
        _client = chromadb.Client()
    if _collection is None:
        _collection = _client.get_or_create_collection("mira_store", embedding_function=DefaultEmbeddingFunction())

def add_text(doc_id: str, text: str, metadata: Dict[str, Any] | None = None) -> None:
    if not AVAILABLE:
        return
    _ensure()
    _collection.upsert(ids=[doc_id], documents=[text], metadatas=[metadata or {}])

def search(query: str, k: int = 5) -> List[Tuple[str, float]]:
    if not AVAILABLE:
        return []
    _ensure()
    res = _collection.query(query_texts=[query], n_results=k)
    docs = (res.get("documents") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    out: List[Tuple[str, float]] = []
    for d, dist in zip(docs, dists):
        # Convert smaller distance to higher score
        score = float(max(0.0, 1.0 - float(dist)))
        out.append((d, score))
    return out

