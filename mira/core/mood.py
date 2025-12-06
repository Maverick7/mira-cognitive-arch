# -*- coding: utf-8 -*-
from __future__ import annotations
import random
from typing import Dict
from .memory import load_identity, update_mood

VALID = {"neutral", "tired", "agitated", "playful", "prayerful"}

def set_mood(m: str) -> str:
    m = (m or "").strip().lower()
    if m not in VALID:
        return f"Invalid mood. Choose {sorted(VALID)}"
    update_mood(m)
    return f"Mood set to {m}"

def auto_drift(last_rewards: Dict[str, float]) -> None:
    """Heuristic mood drift based on shared reward.

    - Low shared reward → drift toward calmer/softer tone ("tired").
    - Good shared reward → small chance to become "playful".
    - Otherwise, occasionally normalize to "neutral".
    """
    try:
        shared = float(last_rewards.get("reward_shared", 0.0))
    except Exception:
        shared = 0.0

    ident = load_identity()
    current = ident.get("mood", "neutral")

    if shared < 0.2 and current != "tired":
        update_mood("tired")
        return
    if shared > 0.6 and random.random() < 0.12 and current != "playful":
        update_mood("playful")
        return
    if random.random() < 0.05 and current != "neutral":
        update_mood("neutral")
        return

