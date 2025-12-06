# -*- coding: utf-8 -*-
import subprocess, textwrap
from ..config import LEFT_MODEL, OLLAMA_BIN, OLLAMA_TIMEOUT, PROVIDER
from ..core.schemas import LEFT_OUTPUT
from .gemini_client import generate_content

def _run_model(model: str, prompt: str) -> str:
    if PROVIDER == "gemini":
        return generate_content(prompt)
        
    # Fallback to Ollama
    proc = subprocess.run(
        [OLLAMA_BIN, "run", model],
        input=prompt.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=OLLAMA_TIMEOUT,
    )
    out = proc.stdout.decode("utf-8", errors="ignore").strip()
    if not out:
        err = proc.stderr.decode("utf-8", errors="ignore")
        return f"[Left: model returned empty. stderr={err[:200]}]"
    return out

def left_reason(user_text: str, memory_snippets: str = "", system_override: str = None) -> str:
    """Logical/analytical hemisphere: structure, correction, plans.
    memory_snippets: pre-retrieved context (short).
    """
    if system_override:
        sys = system_override
    else:
        sys = textwrap.dedent(f"""
        You are the LEFT hemisphere: analytical, precise, corrective.
        Keep output minimal and structured. {LEFT_OUTPUT}
        If the right brain text includes speculation or emotion, keep essence but remove fluff.
        """)
    
    fmt = textwrap.dedent(f"""
    === CONTEXT (memory) ===
    {memory_snippets}
    === INPUT ===
    {user_text}

    Return ONLY JSON as specified. No extra commentary.
    """)
    prompt = sys + "\n" + fmt
    return _run_model(LEFT_MODEL, prompt)
