# -*- coding: utf-8 -*-
"""Mira 3.0 RAG Store: LangChain + Local Embeddings."""
import os
from pathlib import Path
from typing import List, Tuple

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from ..config import DATA_DIR

INDEX_NAME = "mira_v3_index"
INDEX_PATH = DATA_DIR / INDEX_NAME

# Global instances
_embeddings = None
_db = None

def init_store():
    global _embeddings, _db
    
    print("[RAG] Initializing Local Embeddings (all-MiniLM-L6-v2)...")
    _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    if os.path.exists(INDEX_PATH):
        print(f"[RAG] Loading existing index from {INDEX_PATH}...")
        try:
            _db = FAISS.load_local(str(INDEX_PATH), _embeddings, allow_dangerous_deserialization=True)
        except Exception as e:
            print(f"[RAG] Failed to load index: {e}. Creating new one.")
            _db = None
    
    if _db is None:
        print("[RAG] Creating new empty index...")
        # FAISS requires at least one text to initialize via from_texts
        # We'll create a dummy initialization or wait for first add
        # Workaround: Initialize with a greeting
        _db = FAISS.from_texts(["Mira System Initialized."], _embeddings)
        save_store()

def save_store():
    if _db:
        _db.save_local(str(INDEX_PATH))

def add_texts(texts: List[str], metadatas: List[dict] = None):
    if _db is None:
        init_store()
    _db.add_texts(texts, metadatas=metadatas)
    save_store()

def get_doc_count() -> int:
    if _db is None:
        return 0
    return _db.index.ntotal

def search(query: str, k: int = 5, filter: dict = None) -> List[Tuple[str, float]]:
    """Returns list of (content, score). Score is normalized 0-1 if possible.
    
    Args:
        query: Search text
        k: Number of results
        filter: Metadata filter dict, e.g. {'source': 'condensed'}
    """
    if _db is None:
        init_store()
    
    # FAISS returns L2 distance (lower is better)
    # filter argument usage depends on vector store implementation.
    # LangChain FAISS supports direct filter kwarg in recent versions if using proper backend,
    # but generally it filters AFTER or uses metadata if widely supported.
    # For simplicity, if standard FAISS, we might not have efficient filtering unless we use metadata wrapper.
    # However, LangChain's FAISS implementation allows 'filter' in similarity_search_with_score if supported.
    # Let's try passing it.
    
    try:
        docs_and_scores = _db.similarity_search_with_score(query, k=k, filter=filter)
    except Exception:
        # Fallback if filter not supported or empty index
        docs_and_scores = _db.similarity_search_with_score(query, k=k)
    
    results = []
    for doc, score in docs_and_scores:
        # Convert L2 distance to similarity (approximate)
        # 0 distance = 1.0 score
        sim = 1.0 / (1.0 + score)
        results.append((doc.page_content, sim))
    
    return results

AVAILABLE = True
