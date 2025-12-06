# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Tuple
from pathlib import Path
import json
import os

from .memory import append_fact, FACTS_PATH
from .mood import set_mood

# Import vector store utilities
from ..tools.rag_store import add_texts, init_store

def _tail_lines(path: Path, n: int = 10) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[-n:]


# ----------------------------------------------------------------------
# Helper to load arbitrary text into the rag store (simple)
# ----------------------------------------------------------------------
def _load_text_memory(text: str) -> str:
    """Manual memory injection."""
    add_texts([text], [{"source": "manual_command", "type": "user_fact"}])
    return "[Success] Added to M.I.R.A.'s permanent memory."

def _clear_store() -> str:
    """Delete the FAISS index - start fresh."""
    try:
        from ..tools import rag_store
        import shutil
        if rag_store.INDEX_PATH.exists():
            shutil.rmtree(rag_store.INDEX_PATH)
        rag_store.init_store()
        return "[Success] Vector store cleared and re-initialised."
    except Exception as e:
        return f"[Error] clearing store: {e}"


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
    # Load Manual Memory
    if line.startswith("/remember_text "):
        text = line[len("/remember_text "):].strip()
        return True, _load_text_memory(text)
    
    # Load history command (Refers user to CLI)
    if line.startswith("/load_history"):
        return True, "To ingest history, please run: python mira/tools/ingest_history.py <path_to_json> in your terminal."
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
