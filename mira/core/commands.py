# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Tuple
from pathlib import Path
import json
import os

from .memory import append_fact, FACTS_PATH
from .mood import set_mood

# Import vector store utilities
from ..tools.vector_store import (
    add_documents,
    load_batch,
    continue_load,
    _clear_pending,
    init_store,
)

def _tail_lines(path: Path, n: int = 10) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[-n:]

# ----------------------------------------------------------------------
# Helper to load arbitrary JSON files into the vector store (single‑shot)
# ----------------------------------------------------------------------
def _load_json_file(path_str: str) -> str:
    path = Path(path_str).expanduser().resolve()
    if not path.is_file():
        return f"[Error] File not found: {path}"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return f"[Error] Could not parse JSON: {e}"

    docs = []
    if isinstance(data, dict):
        for k, v in data.items():
            docs.append({"id": f"json_{k}", "text": f"{k}: {v}", "type": "user_json"})
    elif isinstance(data, list):
        for i, entry in enumerate(data):
            docs.append({"id": f"json_{i}", "text": json.dumps(entry), "type": "user_json"})
    else:
        return "[Error] JSON must be an object or an array of objects."

    add_documents(docs)
    return f"[Success] Loaded {len(docs)} records from {path.name} into the vector store."

# ----------------------------------------------------------------------
# Helper to load timeline/history files (JSONL or JSON) into the vector store
# ----------------------------------------------------------------------
def _load_history_file(path_str: str) -> str:
    path = Path(path_str).expanduser().resolve()
    if not path.is_file():
        return f"[Error] File not found: {path}"
    docs = []
    
    # Use file modification time as a base "approximate" time if needed
    import datetime
    file_mtime = datetime.datetime.fromtimestamp(path.stat().st_mtime)
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.load(line)
                except Exception:
                    try:
                        obj = json.loads(line)
                    except Exception:
                        obj = {"raw": line}
                
                # If timestamp is missing, inject a default one to help the model understand "when" this happened.
                # We can use a simple index-based offset or just label it as "Past Context".
                if "timestamp" not in obj and "time" not in obj and "date" not in obj:
                    # Inject a synthetic timestamp or label
                    obj["_inferred_context"] = f"Historical entry #{i} from {path.name}"
                
                docs.append({"id": f"history_{i}", "text": json.dumps(obj), "type": "history"})
    except Exception as e:
        return f"[Error] Could not read file: {e}"

    add_documents(docs)
    return f"[Success] Loaded {len(docs)} history entries from {path.name}."

# ----------------------------------------------------------------------
# Batch loading commands for large JSON files
# ----------------------------------------------------------------------
def _load_data_batch(path_str: str, batch_size: int = None) -> str:
    """Load a JSON file in batches. Returns status string.
    If *batch_size* is None, the default from config (MAX_BATCH_SIZE) is used.
    """
    path = Path(path_str).expanduser().resolve()
    if not path.is_file():
        return f"[Error] File not found: {path}"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return f"[Error] Could not parse JSON: {e}"

    docs = []
    if isinstance(data, dict):
        for k, v in data.items():
            docs.append({"id": f"json_{k}", "text": f"{k}: {v}", "type": "user_json"})
    elif isinstance(data, list):
        for i, entry in enumerate(data):
            docs.append({"id": f"json_{i}", "text": json.dumps(entry), "type": "user_json"})
    else:
        return "[Error] JSON must be an object or an array of objects."

    result = load_batch(docs, batch_size=batch_size)
    return f"[Batch] Processed {result['processed']} chunks, {result['remaining']} remaining. Use /continue_load to finish."

def _continue_load(batch_size: int = None) -> str:
    """Continue loading any pending chunks from a previous batch."""
    result = continue_load(batch_size=batch_size)
    return f"[Batch] Processed {result['processed']} chunks, {result['remaining']} remaining."

def _clear_store() -> str:
    """Delete the FAISS index and any pending chunks – start fresh."""
    # Remove index files if they exist
    try:
        from ..tools.vector_store import _index_path
        if _index_path and os.path.exists(_index_path):
            os.remove(_index_path)
            meta_path = _index_path + ".meta.json"
            if os.path.exists(meta_path):
                os.remove(meta_path)
    except Exception:
        pass
    _clear_pending()
    init_store()
    return "[Success] Vector store cleared and re‑initialised."

def handle_command(line: str) -> Tuple[bool, str]:
    """Handle slash commands. Returns (handled, response)."""
    if not line.startswith("/"):
        return False, ""
    # Mood command
    if line.startswith("/mood "):
        m = line.split(" ", 1)[1].strip()
        return True, set_mood(m)
    # Remember command
    if line.startswith("/remember "):
        fact = line.split(" ", 1)[1].strip()
        if not fact:
            return True, "Nothing to remember."
        append_fact(fact)
        return True, "Noted."
    # Dump facts command
    if line.startswith("/dump facts"):
        rows = _tail_lines(FACTS_PATH, 10)
        if not rows:
            return True, "No facts yet."
        return True, "\n".join(rows)
    # Load JSON data command (single‑shot)
    if line.startswith("/load_data "):
        path = line[len("/load_data "):].strip()
        return True, _load_json_file(path)
    # Load history command
    if line.startswith("/load_history "):
        path = line[len("/load_history "):].strip()
        return True, _load_history_file(path)
    # Batch load command
    if line.startswith("/load_data_batch "):
        parts = line.split()
        if len(parts) >= 2:
            path = parts[1]
            batch_size = int(parts[2]) if len(parts) >= 3 else None
            return True, _load_data_batch(path, batch_size)
        return True, "[Error] Usage: /load_data_batch <path> [batch_size]"
    # Continue loading pending chunks
    if line.startswith("/continue_load"):
        parts = line.split()
        batch_size = int(parts[1]) if len(parts) >= 2 else None
        return True, _continue_load(batch_size)
    # Clear the vector store
    if line.startswith("/clear_store"):
        return True, _clear_store()
    
    # Reflect command (force update of self-narrative)
    if line.startswith("/reflect"):
        try:
            from .self_narrative import self_reflect
            # Extract optional context
            context = line[len("/reflect"):].strip()
            if not context:
                context = "User manually requested self-reflection."
            
            # Use threading to not block the UI (generation takes time)
            import threading
            t = threading.Thread(target=self_reflect, args=(context,))
            t.start()
            return True, "Triggered self-reflection. Check the logs or wait for the next turn to see the effect."
        except Exception as e:
            return True, f"Reflection error: {e}"

    return True, "Unknown command."
