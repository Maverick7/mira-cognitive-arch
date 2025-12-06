# -*- coding: utf-8 -*-
"""Data Importer for Mira.
Ingests ChatGPT history (conversations.json) into the local vector store (RAG).
"""
import json
import sys
import os
from pathlib import Path

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from mira.tools import rag_store

def extract_conversations(json_path: str):
    """Generates (text, metadata) tuples from ChatGPT JSON."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"Found {len(data)} conversations. Extracting clean text...")
    
    batch_texts = []
    batch_metads = []
    
    count = 0
    for conv in data:
        title = conv.get("title", "Unknown")
        mapping = conv.get("mapping", {})
        node_id = conv.get("current_node")
        
        # Traverse backwards
        messages = []
        while node_id:
            node = mapping.get(node_id)
            if not node: break
            msg = node.get("message")
            if msg:
                role = msg.get("author", {}).get("role")
                parts = msg.get("content", {}).get("parts", [])
                text = "".join(str(p) for p in parts if isinstance(p, str))
                if text and role in ("user", "assistant"):
                    messages.append(f"{role.capitalize()}: {text}")
            node_id = node.get("parent")
        
        if messages:
            messages.reverse()
            full_text = "\n\n".join(messages)
            if len(full_text) > 50: # Skip empty/tiny
                batch_texts.append(full_text)
                batch_metads.append({"source": "chatgpt", "title": title})
                count += 1
                
    return batch_texts, batch_metads

def run_import(json_path: str):
    print(f"Reading {json_path}...")
    texts, metas = extract_conversations(json_path)
    
    print(f"Extracted {len(texts)} valid conversations.")
    print("Ingesting into Local RAG Store (Reference: rag_store.py)...")
    
    # Batch ingest
    batch_size = 100
    total = len(texts)
    
    rag_store.init_store()
    
    for i in range(0, total, batch_size):
        end = min(i + batch_size, total)
        print(f"Indexing {i} to {end}...")
        rag_store.add_texts(texts[i:end], metas[i:end])
        
    print("Done! Data is now in 'mira_v3_index'.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest_history.py <conversations.json>")
    else:
        run_import(sys.argv[1])
