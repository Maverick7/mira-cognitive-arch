# -*- coding: utf-8 -*-
import time
from typing import Dict, Any, Tuple

def encode_state(user_text: str, mood: str) -> Dict[str, Any]:
    return {"t": time.time(), "last_user": user_text, "mood": mood}

def step(state: Dict[str, Any], metrics: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, float]]:
    # Simple reward signals: length within range, logical quality proxy, warmth proxy.
    L = metrics.get("final_text_length", 0)
    logical = float(metrics.get("logical_quality", 0.5))
    # penalize too long or too short
    if L < 10: span = -0.2
    elif L > 600: span = -0.2
    else: span = 0.2
    reward_left = logical
    reward_right = 0.2 + span
    reward_shared = (reward_left + reward_right) / 2.0
    rewards = {
        "reward_left": float(round(reward_left, 3)),
        "reward_right": float(round(reward_right, 3)),
        "reward_shared": float(round(reward_shared, 3)),
    }
    state.update({"last_rewards": rewards})
    return state, rewards
