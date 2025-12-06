# -*- coding: utf-8 -*-
"""Voice synthesis helper using edge-tts."""
import asyncio
import os
import tempfile
try:
    import edge_tts
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

VOICE = "en-US-JennyNeural"  # Default "emotional" voice (Jenny is usually good/warm)
# Other good options: "en-US-AriaNeural", "en-GB-SoniaNeural"

async def _gen_audio(text: str, out_path: str) -> None:
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(out_path)

def generate_audio(text: str) -> str | None:
    """Generates audio file for the text and returns the path.
    Returns None if edge-tts is not available.
    """
    if not AVAILABLE:
        return None
    
    # Create a proper temporary file that persists
    # We use delete=False so we can read it in the main app
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    
    try:
        asyncio.run(_gen_audio(text, path))
        return path
    except Exception as e:
        print(f"[Voice Error] {e}")
        return None
