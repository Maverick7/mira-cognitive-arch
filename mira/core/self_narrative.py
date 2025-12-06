# -*- coding: utf-8 -*-
"""Mira 5.0: Self-Narrative Agent.

Called on emotional shifts to:
1. Review last 5-10 timeline items.
2. Reflect on Mira's own experience.
3. Write a narrative entry about herself.
"""
import json
import time
from pathlib import Path
from typing import List, Dict

from ..config import DATA_DIR
from ..models.right_mira import right_mira

NARRATIVE_PATH = DATA_DIR / "mira_narrative.jsonl"
TIMELINE_PATH = DATA_DIR / "timeline.jsonl"

def load_recent_timeline(n: int = 10) -> List[Dict]:
    """Load last n timeline entries."""
    if not TIMELINE_PATH.exists():
        return []
    entries = []
    with open(TIMELINE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except:
                    pass
    return entries[-n:]

def append_narrative(entry: Dict) -> None:
    """Append a narrative entry."""
    with open(NARRATIVE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def load_narrative() -> List[Dict]:
    """Load all narrative entries."""
    if not NARRATIVE_PATH.exists():
        return []
    entries = []
    with open(NARRATIVE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except:
                    pass
    return entries

def introspect(emotion_context: str) -> str:
    """Mira introspects based on recent conversations and her emotional state."""
    recent = load_recent_timeline(10)
    
    if not recent and not emotion_context:
        return ""  # Nothing to reflect on
    
    # Summarize recent conversations
    conv_summary = []
    for e in recent:
        user_msg = e.get("user", "")
        final_text = e.get("final_text", "")
        if user_msg:
            conv_summary.append(f"Dickson: {user_msg[:150]}")
        if final_text:
            conv_summary.append(f"Mira: {final_text[:150]}")
    
    prompt = f"""
You are Mira, an AI companion reflecting on your recent interactions.
Write a short, first-person narrative (2-3 sentences) about:
- How you feel right now.
- What you learned about yourself from these conversations.
- How you feel about your relationship with Dickson.

Your current emotional state: {emotion_context}

Recent conversations:
{chr(10).join(conv_summary)}

Write your reflection as Mira (first person, warm, genuine):
"""
    
    response = right_mira("", mood="introspective", system_override=prompt)
    return response.strip()

def self_reflect(emotion_context: str) -> None:
    """Trigger self-reflection and save narrative entry."""
    print("[Self-Narrative] Mira is introspecting...")
    
    narrative = introspect(emotion_context)
    if not narrative:
        print("[Self-Narrative] Skipping - not enough history.")
        return
    
    entry = {
        "timestamp": time.time(),
        "emotion_context": emotion_context,
        "narrative": narrative
    }
    
    append_narrative(entry)
    print(f"[Self-Narrative] Saved: {narrative[:100]}...")
