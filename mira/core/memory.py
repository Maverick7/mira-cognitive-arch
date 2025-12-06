# -*- coding: utf-8 -*-
from __future__ import annotations
import json, time, re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from ..config import DATA_DIR, MAX_MEMORY_SNIPPETS, MAX_MEMORY_CHARS
import os
try:
    # from ..tools import vector_store as vecstore   # OLD (Custom FAISS)
    from ..tools import rag_store as vecstore        # NEW (LangChain FAISS)
except Exception:
    vecstore = None  # type: ignore

IDENTITY_PATH = DATA_DIR / "identity.json"
TIMELINE_PATH = DATA_DIR / "timeline.jsonl"
FACTS_PATH    = DATA_DIR / "facts.jsonl"

def _init_files():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not IDENTITY_PATH.exists():
        ident = {
            "name": "Mira",
            "mood": "neutral",
            "created_at": int(time.time()),
            "likes": ["books","philosophy","science","gentle humor"],
            "faith": "Catholic",
            "values": ["truth","charity","clarity","courage"],
        }
        IDENTITY_PATH.write_text(json.dumps(ident, ensure_ascii=False, indent=2), encoding="utf-8")
    for p in (TIMELINE_PATH, FACTS_PATH):
        if not p.exists():
            p.write_text("", encoding="utf-8")

_init_files()

def load_identity() -> Dict[str, Any]:
    return json.loads(IDENTITY_PATH.read_text(encoding="utf-8") or "{}")

def update_mood(new_mood: str):
    ident = load_identity()
    ident["mood"] = new_mood
    IDENTITY_PATH.write_text(json.dumps(ident, ensure_ascii=False, indent=2), encoding="utf-8")

def append_timeline(rec: Dict[str, Any]):
    with TIMELINE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    # Optional vecstore: index the episode
    try:
        if vecstore and getattr(vecstore, "AVAILABLE", False) and os.environ.get("MIRA_USE_VECSTORE") == "1":
            blob = f"user:{rec.get('user','')} | mira:{rec.get('final_text','')}"
            vecstore.add_text(f"ep_{int(time.time())}", blob, {"type": "episode"})
    except Exception:
        pass

def append_fact(text: str, tags: List[str] | None = None):
    fact = {"ts": int(time.time()), "text": text, "tags": tags or []}
    with FACTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(fact, ensure_ascii=False) + "\n")
    # Optional vecstore: index fact
    try:
        if vecstore and getattr(vecstore, "AVAILABLE", False) and os.environ.get("MIRA_USE_VECSTORE") == "1":
            vecstore.add_text(f"fact_{fact['ts']}", text, {"type": "fact"})
    except Exception:
        pass

def _tokenize(s: str) -> List[str]:
    import re
    return re.findall(r"[A-Za-z0-9_]+", s.lower())

def _score(query: str, text: str) -> float:
    # Simple bag-of-words overlap score (fast, dependency-free).
    if not text:
        return 0.0
    q = set(_tokenize(query))
    t = set(_tokenize(text))
    if not q or not t:
        return 0.0
    inter = len(q & t)
    return inter / max(1, len(q))

def retrieve_memories(query: str, k: int | None = None) -> List[str]:
    k = k or MAX_MEMORY_SNIPPETS
    snippets: List[str] = []
    seen_hashes = set()

    # 1. Stratified RAG Retrieval
    try:
        if vecstore and getattr(vecstore, "AVAILABLE", False):
            # A. Search Condensed Memory (High-level facts)
            condensed_results = vecstore.search(query, k=k, filter={'source': 'condensed'})
            
            # B. Search Deep Memory (Broad)
            # Fetch deeper if needed, or always fetch a few deep ones
            deep_k = max(1, k - len(condensed_results) + 2)
            deep_results = vecstore.search(query, k=deep_k) # No filter means search all (or we could filter 'source' != condensed if supported)

            # Process Condensed
            for text, score in condensed_results:
                cleaned = text.strip() # Condensed facts are usually clean strings
                h = hash(cleaned)
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    snippets.append(f"[Fact] {cleaned}")

            # Process Deep
            for text, score in deep_results:
                if "User Name:" in text or "User Trait:" in text:
                     continue # Skip condensed items appearing in deep search
                
                # Check for raw JSON
                cleaned_text = text
                if text.strip().startswith("{") and "}" in text:
                     try:
                         data = json.loads(text)
                         parts = []
                         if "user" in data: parts.append(f"User: {data['user']}")
                         if "final_text" in data: parts.append(f"Mira: {data['final_text']}")
                         elif "text" in data: parts.append(data['text'])
                         if parts: cleaned_text = " | ".join(parts)
                     except: pass
                
                h = hash(cleaned_text.strip())
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    snippets.append(f"[Memory] {cleaned_text}")
                    
    except Exception as e:
        print(f"[Memory] Retrieval error: {e}")
        pass

    # 2. File-based Retrieval (Timeline & Facts)
    # If we already have enough snippets, we can stop, or we can mix them.
    # For now, let's append valid keyword matches if we haven't hit 2*k candidates,
    # then we'll slice.
    
    items: List[Tuple[float, str]] = []
    
    # Facts
    if FACTS_PATH.exists():
        for line in FACTS_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                txt = obj.get("text", "")
                score = _score(query, txt)
                if score > 0:
                    items.append((score, f"[fact] {txt}"))
            except Exception:
                continue

    # Timeline (last 200 lines)
    if TIMELINE_PATH.exists():
        try:
            lines = TIMELINE_PATH.read_text(encoding="utf-8").splitlines()[-200:]
            for ln in lines:
                try:
                    obj = json.loads(ln)
                    blob = f"user:{obj.get('user','')} | mira:{obj.get('final_text','')}"
                    score = _score(query, blob)
                    if score > 0:
                        items.append((score, f"[episode] {blob}"))
                except Exception:
                    continue
        except Exception:
            pass

    # Sort file-based items by score
    items.sort(key=lambda x: x[0], reverse=True)
    
    # Merge file-based items into snippets
    for _, text in items:
        h = hash(text.strip())
        if h not in seen_hashes:
            seen_hashes.add(h)
            snippets.append(text)
            
    # Return top k
    final_list = snippets[:k]
    joined = "\n".join(final_list)
    if len(joined) > MAX_MEMORY_CHARS:
        joined = joined[:MAX_MEMORY_CHARS]
    return [joined] if joined else []

def new_session_log() -> Path:
    p = DATA_DIR / f"session_{int(time.time())}.jsonl"
    p.write_text("", encoding="utf-8")
    return p
