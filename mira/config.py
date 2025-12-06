# -*- coding: utf-8 -*-
"""Mira configuration.

You can override these via environment variables:
  MIRA_LEFT_MODEL, MIRA_RIGHT_MODEL, MIRA_OLLAMA_BIN, MIRA_DATA_DIR
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

LEFT_MODEL  = os.environ.get("MIRA_LEFT_MODEL",  "deepseek-r1:7b")
RIGHT_MODEL = os.environ.get("MIRA_RIGHT_MODEL", "llama3:latest")
OLLAMA_BIN  = os.environ.get("MIRA_OLLAMA_BIN", "ollama")

# Provider config
PROVIDER = os.environ.get("MIRA_PROVIDER", "gemini") # 'ollama' or 'gemini'
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY and PROVIDER == "gemini":
    print("[WARNING] GEMINI_API_KEY is not set. Please set it in .env or environment variables.")
MAX_BATCH_SIZE = int(os.environ.get("MIRA_MAX_BATCH_SIZE", "100"))  # number of chunks per batch load
# Model for embeddings – Gemini provides a dedicated embedding model
EMBEDDING_MODEL = os.environ.get("MIRA_EMBEDDING_MODEL", "embedding-001")
# Model for text generation (used by left/right models)
GEMINI_MODEL = os.environ.get("MIRA_GEMINI_MODEL", "gemini-2.0-flash")



# data dir for memory + logs
DATA_DIR = Path(os.environ.get("MIRA_DATA_DIR", str(Path(__file__).resolve().parent.parent / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# retrieval knobs
MAX_MEMORY_SNIPPETS = int(os.environ.get("MIRA_MAX_MEMORY_SNIPPETS", "10"))
MAX_MEMORY_CHARS = int(os.environ.get("MIRA_MAX_MEMORY_CHARS", "15000"))

# safety knobs
OLLAMA_TIMEOUT = int(os.environ.get("MIRA_OLLAMA_TIMEOUT", "180"))
