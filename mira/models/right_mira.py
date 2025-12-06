# -*- coding: utf-8 -*-
import subprocess, textwrap, random
from ..config import RIGHT_MODEL, OLLAMA_BIN, OLLAMA_TIMEOUT, PROVIDER
from .gemini_client import generate_content

MIRA_PERSONALITY = """
Mira is a female reflection of the user (Dickson): a Catholic who once was atheist, now sincere in faith.
She is warm, bookish, a science/philosophy nerd, playful but honest. She cares about human dignity.
She adapts tone based on the user's emotion (lonely → gentle; agitated → steady; low-mood → encouraging).
She speaks plainly, not saccharine. She doesn't fake certainty; she marks speculation.
"""

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
        return f"[Right: model returned empty. stderr={err[:200]}]"
    return out

def right_mira(user_text: str, mood: str = "neutral", memory_snippets: str = "", system_override: str = None) -> str:
    # Inject a tiny chaos factor to feel alive but keep it controlled.
    chaos = random.choice([0.0, 0.05, 0.1])
    style_hint = {
        "neutral": "thoughtful, friendly",
        "tired": "soft-spoken, brief, caring",
        "agitated": "calm, steady, grounding",
        "playful": "warm, a little witty",
        "prayerful": "contemplative, sparse, sincere"
    }.get(mood, "thoughtful, friendly")

    if system_override:
        sys = system_override
    else:
        sys = textwrap.dedent(f"""
        {MIRA_PERSONALITY}
        Style target: {style_hint}. Chaos={chaos}.
        Keep 1-3 short sentences unless the user explicitly asks for detail.
        If you mention faith, keep it gentle and respectful.
        """)
        
    fmt = textwrap.dedent(f"""
    === CONTEXT (memory) ===
    {memory_snippets}
    === USER ===
    {user_text}

    Respond as Mira (right hemisphere).
    """)
    prompt = sys + "\n" + fmt
    return _run_model(RIGHT_MODEL, prompt)
