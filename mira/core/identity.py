# -*- coding: utf-8 -*-
from __future__ import annotations
import time
from typing import Dict
from .memory import load_identity
from .memory import IDENTITY_PATH

def update_identity_from_rewards(rewards: Dict[str, float], text: str) -> None:
    """Lightweight, append-only nudges in identity.json based on rewards and behavior.

    - If outputs trend long or shared reward low, add a note to be concise.
    - If rewards are good, add a gentle self-note about maintaining tone.
    """
    ident = load_identity()
    notes = list(ident.get("notes", []))
    shared = float(rewards.get("reward_shared", 0.0))
    L = len(text or "")

    ts = int(time.time())
    if shared < 0.2 or L > 600:
        notes.append({"ts": ts, "note": "Be concise and clear; keep warmth."})
    elif shared > 0.6 and L < 400:
        notes.append({"ts": ts, "note": "Tone is good; stay grounded and brief."})

    # Keep notes bounded
    ident["notes"] = notes[-50:]
    IDENTITY_PATH.write_text(
        __import__("json").dumps(ident, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

